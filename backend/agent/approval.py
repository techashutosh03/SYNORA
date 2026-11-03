import asyncio
import uuid
import time
import difflib
from typing import Dict, Any, Optional, List, Callable, Tuple
from pydantic import BaseModel, Field

from backend.database.sqlite import (
    save_pending_approval_db,
    update_approval_status_db,
    get_approval_record_db,
    get_active_pending_approvals_db,
    cleanup_pending_approvals_db
)
from backend.core.security import generate_session_token, verify_session_token

class PendingAction(BaseModel):
    action_id: str
    session_id: str
    user_id: Optional[str] = "default_user"
    workspace_root: str = "."
    tool_name: str
    arguments: Dict[str, Any]
    reason: str
    diff_preview: Optional[str] = None
    command_preview: Optional[str] = None
    auth_token: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    expires_at: float = Field(default=0.0)
    status: str = "pending"  # "pending", "approved", "rejected", "timed_out", "cancelled"

class ApprovalManager:
    """
    Manages interactive human-in-the-loop approvals for Claw Code mutating tools.
    Pauses agent loop execution until the user explicitly approves or rejects.
    
    Features:
    - User and session validation (prevents other users from approving actions)
    - Auto-expiration (TTL cleanup)
    - Session disconnect/cancellation cleanup
    - Durable SQLite backing (works across server worker processes and restarts)
    """

    def __init__(self):
        self._pending_actions: Dict[str, PendingAction] = {}
        self._futures: Dict[str, asyncio.Future] = {}
        self._default_callback: Optional[Callable[[str, Dict[str, Any], str], bool]] = None

    def set_default_callback(self, cb: Optional[Callable[[str, Dict[str, Any], str], bool]]):
        """Sets a synchronous or asynchronous callback for interactive environments like CLI."""
        self._default_callback = cb

    def register_pending_action(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        reason: str,
        user_id: Optional[str] = "default_user",
        timeout_seconds: float = 60.0,
        workspace_root: str = ".",
        diff_preview: Optional[str] = None,
        command_preview: Optional[str] = None
    ) -> str:
        now = time.time()
        expires_at = now + timeout_seconds
        action_id = str(uuid.uuid4())

        # Auto-generate diff or command preview if not explicitly passed
        if diff_preview is None:
            if tool_name == "edit_file":
                p = arguments.get("path", "file")
                old_lines = arguments.get("old_string", "").splitlines(keepends=True)
                new_lines = arguments.get("new_string", "").splitlines(keepends=True)
                diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{p}", tofile=f"b/{p}"))
                diff_preview = "".join(diff) if diff else f"--- a/{p}\n+++ b/{p}\n@@ replace @@\n- {arguments.get('old_string', '')}\n+ {arguments.get('new_string', '')}"
            elif tool_name == "write_file":
                p = arguments.get("path", "file")
                content = arguments.get("content", "")
                preview_lines = [f"+ {l}" for l in content.splitlines()[:40]]
                diff_preview = f"--- /dev/null\n+++ b/{p}\n@@ new file @@\n" + "\n".join(preview_lines)

        if command_preview is None and tool_name == "bash":
            cmd = arguments.get("command", "")
            command_preview = f"[{workspace_root}] $ {cmd}"

        # Generate authenticated session/action token
        auth_token = generate_session_token(
            session_id=session_id,
            user_id=user_id or "default_user",
            ttl_seconds=int(timeout_seconds) + 60,
            metadata={"action_id": action_id, "tool": tool_name}
        )

        action = PendingAction(
            action_id=action_id,
            session_id=session_id,
            user_id=user_id or "default_user",
            workspace_root=workspace_root,
            tool_name=tool_name,
            arguments=arguments,
            reason=reason,
            diff_preview=diff_preview,
            command_preview=command_preview,
            auth_token=auth_token,
            created_at=now,
            expires_at=expires_at,
            status="pending"
        )
        self._pending_actions[action_id] = action

        # Persist to SQLite for cross-worker durable coordination
        try:
            save_pending_approval_db(
                action_id=action_id,
                session_id=session_id,
                user_id=user_id or "default_user",
                tool_name=tool_name,
                arguments=arguments,
                reason=reason,
                created_at=now,
                expires_at=expires_at,
                workspace_root=workspace_root,
                diff_preview=diff_preview,
                command_preview=command_preview
            )
        except Exception:
            pass

        return action_id

    async def wait_for_approval(
        self,
        action_id: str,
        timeout_seconds: float = 60.0,
        confirm_callback: Optional[Callable[[str, Dict[str, Any], str], Any]] = None
    ) -> bool:
        """
        Pauses execution until the user approves/rejects the action or the timeout expires.
        Polls both the local in-memory future and SQLite backing table to support multi-worker ASGI.
        """
        action = self._pending_actions.get(action_id)
        if not action:
            rec = get_approval_record_db(action_id)
            if rec:
                action = PendingAction(**rec)
                self._pending_actions[action_id] = action
            else:
                return False

        if action.status == "approved":
            return True
        if action.status in ("rejected", "timed_out", "cancelled"):
            return False

        # If a direct callback is registered (e.g. CLI prompt), invoke it
        cb = confirm_callback or self._default_callback
        if cb:
            try:
                res = cb(action.tool_name, action.arguments, action.reason)
                if asyncio.iscoroutine(res):
                    res = await res
                approved = bool(res)
                action.status = "approved" if approved else "rejected"
                update_approval_status_db(action_id, action.status)
                return approved
            except Exception:
                action.status = "rejected"
                update_approval_status_db(action_id, "rejected")
                return False

        # Otherwise, create an async future for web / SSE API approval
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._futures[action_id] = future

        deadline = time.time() + timeout_seconds
        try:
            while time.time() < deadline:
                # 1. Check local future
                if future.done():
                    approved = future.result()
                    action.status = "approved" if approved else "rejected"
                    update_approval_status_db(action_id, action.status)
                    return bool(approved)

                # 2. Check SQLite in case resolved by another worker process
                db_rec = get_approval_record_db(action_id)
                if db_rec and db_rec.get("status") in ("approved", "rejected", "timed_out", "cancelled"):
                    db_st = db_rec["status"]
                    action.status = db_st
                    approved = (db_st == "approved")
                    if not future.done():
                        future.set_result(approved)
                    return approved

                # Wait shortly before next poll
                try:
                    await asyncio.wait_for(asyncio.shield(future), timeout=0.25)
                except asyncio.TimeoutError:
                    pass

            # Timeout reached
            action.status = "timed_out"
            update_approval_status_db(action_id, "timed_out")
            return False
        finally:
            self._futures.pop(action_id, None)

    def resolve_action(
        self,
        action_id: str,
        approved: bool,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_token: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Resolves a pending action.
        Enforces user and session isolation and cryptographic token authentication:
        prevents unauthorized cross-session/cross-user approvals and forged requests.
        """
        action = self._pending_actions.get(action_id)
        if not action:
            rec = get_approval_record_db(action_id)
            if rec:
                action = PendingAction(**rec)
                self._pending_actions[action_id] = action

        if not action:
            return False, f"Action '{action_id}' not found."

        # Cryptographic session token verification (if token supplied or action enforces token)
        if session_token:
            verified = verify_session_token(session_token)
            if not verified:
                return False, "Security violation: Invalid, forged, or expired session authentication token."
            tok_session_id, tok_user_id = verified
            if tok_session_id != action.session_id:
                return False, f"Security violation: Token session '{tok_session_id}' does not match action session '{action.session_id}'."
            if tok_user_id != action.user_id and action.user_id != "default_user":
                return False, f"Security violation: Token user '{tok_user_id}' does not match action user '{action.user_id}'."

        # Check expiration
        if action.expires_at and time.time() > action.expires_at:
            action.status = "timed_out"
            update_approval_status_db(action_id, "timed_out")
            if action_id in self._futures and not self._futures[action_id].done():
                self._futures[action_id].set_result(False)
            return False, "Action has expired (timed out)."

        # User and Session isolation checks
        if session_id and action.session_id and action.session_id != session_id:
            return False, f"Security violation: Action '{action_id}' belongs to session '{action.session_id}', not '{session_id}'."

        if user_id and action.user_id and action.user_id != user_id and action.user_id != "default_user":
            return False, f"Security violation: Action '{action_id}' belongs to user '{action.user_id}', not '{user_id}'."

        new_status = "approved" if approved else "rejected"
        action.status = new_status
        update_approval_status_db(action_id, new_status)

        if action_id in self._futures and not self._futures[action_id].done():
            self._futures[action_id].set_result(approved)

        return True, f"Action {new_status} successfully."

    def cancel_action(self, action_id: str, reason: str = "cancelled") -> bool:
        """Explicitly cancels an action."""
        action = self._pending_actions.get(action_id)
        if action:
            action.status = reason
        update_approval_status_db(action_id, reason)
        if action_id in self._futures and not self._futures[action_id].done():
            self._futures[action_id].set_result(False)
        return True

    def cleanup_session(self, session_id: str, reason: str = "client_disconnected") -> int:
        """
        Cancels all pending actions for a session when user disconnects or cancels request.
        """
        cleaned = 0
        for aid, action in list(self._pending_actions.items()):
            if action.session_id == session_id and action.status == "pending":
                action.status = reason
                if aid in self._futures and not self._futures[aid].done():
                    self._futures[aid].set_result(False)
                cleaned += 1

        db_cleaned = cleanup_pending_approvals_db(session_id=session_id, reason=reason)
        return max(cleaned, db_cleaned)

    def prune_expired_actions(self) -> int:
        """Prunes expired pending actions."""
        now = time.time()
        pruned = 0
        for aid, action in list(self._pending_actions.items()):
            if action.status == "pending" and action.expires_at and now > action.expires_at:
                action.status = "timed_out"
                if aid in self._futures and not self._futures[aid].done():
                    self._futures[aid].set_result(False)
                update_approval_status_db(aid, "timed_out")
                pruned += 1
        return pruned

    def get_pending_actions(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        self.prune_expired_actions()
        # Merge memory + SQLite
        db_actions = get_active_pending_approvals_db(session_id=session_id, user_id=user_id)
        db_ids = {a["action_id"] for a in db_actions}
        merged = list(db_actions)

        for a in self._pending_actions.values():
            if a.status == "pending" and a.action_id not in db_ids:
                if (session_id is None or a.session_id == session_id) and \
                   (user_id is None or a.user_id == user_id or a.user_id == "default_user"):
                    merged.append(a.model_dump())
        return merged

approval_manager = ApprovalManager()
