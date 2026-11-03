import unittest
import asyncio
import json
import tempfile
import shutil
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.agent.permissions import PermissionEnforcer, permission_scope
from backend.agent.approval import ApprovalManager, PendingAction
from backend.database.sqlite import cleanup_pending_approvals_db
from backend.agent.loop import (
    compute_grounded_completion,
    is_test_command,
    verify_test_output_evidence,
    detect_workspace_file_changes,
    AgentLoop
)
from backend.agent.tools import ToolManager

class TestAgentRefinements(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="synora_refinements_test_")
        self.tool_mgr = ToolManager(workspace_root=self.test_dir)
        self.enforcer = PermissionEnforcer(workspace_root=self.test_dir)
        self.client = TestClient(app)
        cleanup_pending_approvals_db()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        cleanup_pending_approvals_db()

    # =========================================================================
    # 1. PERMISSION ISOLATION & STRICT DEFAULTS
    # =========================================================================

    def test_permission_defaults_to_ask_mode(self):
        """Verifies that the default permission mode is 'ask' (secure human-in-the-loop)."""
        fresh_enforcer = PermissionEnforcer(workspace_root=self.test_dir)
        self.assertEqual(fresh_enforcer.mode, "ask")

        # In 'ask' mode, write_file and bash require user confirmation
        dec_write = fresh_enforcer.check_tool_permission("write_file", {"path": "test.txt", "content": "data"})
        self.assertTrue(dec_write.requires_confirmation)

        dec_bash = fresh_enforcer.check_tool_permission("bash", {"command": "echo hello"})
        self.assertTrue(dec_bash.requires_confirmation)

    def test_permission_scope_isolation_concurrent(self):
        """
        Verifies that concurrent async tasks with different permission_scope
        modes do not clobber each other's permissions.
        """
        async def task_read_only():
            with permission_scope("read_only"):
                await asyncio.sleep(0.01)
                dec = self.enforcer.check_tool_permission("write_file", {"path": "a.txt", "content": "data"})
                await asyncio.sleep(0.01)
                dec_read = self.enforcer.check_tool_permission("read_file", {"path": "a.txt"})
                return dec.allowed, dec_read.allowed

        async def task_autonomous():
            with permission_scope("autonomous"):
                await asyncio.sleep(0.01)
                dec = self.enforcer.check_tool_permission("write_file", {"path": "b.txt", "content": "data"})
                await asyncio.sleep(0.01)
                dec_bash = self.enforcer.check_tool_permission("bash", {"command": "ls -la"})
                return dec.allowed, dec_bash.allowed

        async def task_ask():
            with permission_scope("ask"):
                await asyncio.sleep(0.01)
                dec = self.enforcer.check_tool_permission("bash", {"command": "echo test"})
                return dec.requires_confirmation

        async def run_all():
            return await asyncio.gather(task_read_only(), task_autonomous(), task_ask())

        (ro_write, ro_read), (auto_write, auto_bash), ask_confirm = asyncio.run(run_all())

        # In read_only task: write is blocked, read is allowed
        self.assertFalse(ro_write)
        self.assertTrue(ro_read)

        # In autonomous task running at the exact same time: write and bash are allowed
        self.assertTrue(auto_write)
        self.assertTrue(auto_bash)

        # In ask task running at the exact same time: bash requires confirmation
        self.assertTrue(ask_confirm)

    def test_permission_mode_override_param(self):
        """Passing explicit mode parameter overrides the enforcer's context mode."""
        with permission_scope("autonomous"):
            dec = self.enforcer.check_tool_permission("write_file", {"path": "test.txt"}, mode="read_only")
            self.assertFalse(dec.allowed)
            self.assertIn("read_only", dec.reason)

    def test_read_only_tools_whitelist(self):
        """Read-only mode strictly allows inspection tools and denies mutating tools."""
        with permission_scope("read_only"):
            for tool in ["read_file", "list_dir", "grep_search", "glob_files", "git_status", "git_diff"]:
                with self.subTest(tool=tool):
                    dec = self.enforcer.check_tool_permission(tool, {})
                    self.assertTrue(dec.allowed, f"Tool {tool} should be allowed in read_only mode")

            for mut in ["write_file", "edit_file", "bash"]:
                with self.subTest(mut=mut):
                    dec = self.enforcer.check_tool_permission(mut, {})
                    self.assertFalse(dec.allowed, f"Mutating tool {mut} must be denied in read_only mode")

    # =========================================================================
    # 2. APPROVALS: USER & SESSION ISOLATION, DURABILITY, LIFECYCLE
    # =========================================================================

    def test_approval_manager_pause_and_approve(self):
        """
        Verifies that wait_for_approval pauses execution until resolve_action is called.
        """
        manager = ApprovalManager()
        action_id = manager.register_pending_action(
            session_id="sess_123",
            tool_name="edit_file",
            arguments={"path": "auth.py", "replace": "new_code"},
            reason="Editing auth file requires user approval."
        )

        # Verify action is in pending list
        pending = manager.get_pending_actions("sess_123")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["action_id"], action_id)
        self.assertEqual(pending[0]["tool_name"], "edit_file")

        async def async_worker():
            return await manager.wait_for_approval(action_id, timeout_seconds=2.0)

        async def resolver():
            await asyncio.sleep(0.05)
            self.assertEqual(len(manager.get_pending_actions("sess_123")), 1)
            success, msg = manager.resolve_action(action_id, approved=True, session_id="sess_123")
            self.assertTrue(success)

        async def run_pair():
            worker_task = asyncio.create_task(async_worker())
            resolver_task = asyncio.create_task(resolver())
            result, _ = await asyncio.gather(worker_task, resolver_task)
            return result

        approved = asyncio.run(run_pair())
        self.assertTrue(approved)
        self.assertEqual(len(manager.get_pending_actions("sess_123")), 0)

    def test_approval_user_and_session_isolation(self):
        """
        Security verification: Prevents another user or mismatched session from approving an action.
        """
        manager = ApprovalManager()
        action_id = manager.register_pending_action(
            session_id="session_alpha",
            user_id="alice",
            tool_name="bash",
            arguments={"command": "rm file.txt"},
            reason="Security boundary test"
        )

        # 1. Attempt approval with mismatched session_id -> MUST FAIL
        success_bad_sess, msg_bad_sess = manager.resolve_action(
            action_id=action_id,
            approved=True,
            session_id="session_beta",
            user_id="alice"
        )
        self.assertFalse(success_bad_sess)
        self.assertIn("Security violation", msg_bad_sess)
        self.assertIn("session", msg_bad_sess)

        # 2. Attempt approval with mismatched user_id -> MUST FAIL
        success_bad_user, msg_bad_user = manager.resolve_action(
            action_id=action_id,
            approved=True,
            session_id="session_alpha",
            user_id="mallory"
        )
        self.assertFalse(success_bad_user)
        self.assertIn("Security violation", msg_bad_user)
        self.assertIn("user", msg_bad_user)

        # 3. Legitimate user & session -> SUCCEEDS
        success_good, msg_good = manager.resolve_action(
            action_id=action_id,
            approved=True,
            session_id="session_alpha",
            user_id="alice"
        )
        self.assertTrue(success_good)
        self.assertIn("approved", msg_good)

    def test_approval_api_security_enforcement(self):
        """Tests that the API enforces session and user boundaries with HTTP 403."""
        from backend.main import approval_manager as global_approval_mgr

        action_id = global_approval_mgr.register_pending_action(
            session_id="sec_sess_1",
            user_id="user_admin",
            tool_name="edit_file",
            arguments={"path": "critical.py"},
            reason="API Security Test"
        )

        # Mismatched session returns 403 Forbidden
        bad_res = self.client.post("/api/agent/confirm", json={
            "action_id": action_id,
            "approved": True,
            "session_id": "attacker_session",
            "user_id": "user_admin"
        })
        self.assertEqual(bad_res.status_code, 403)

        # Matching session succeeds with 200 OK
        good_res = self.client.post("/api/agent/confirm", json={
            "action_id": action_id,
            "approved": True,
            "session_id": "sec_sess_1",
            "user_id": "user_admin"
        })
        self.assertEqual(good_res.status_code, 200)
        self.assertTrue(good_res.json()["resolved"])

    def test_approval_cleanup_on_disconnect(self):
        """Verifies cleanup_session aborts and cleans up all pending actions for a session."""
        manager = ApprovalManager()
        a1 = manager.register_pending_action(session_id="sess_dc", tool_name="bash", arguments={}, reason="r1")
        a2 = manager.register_pending_action(session_id="sess_dc", tool_name="edit_file", arguments={}, reason="r2")
        a_other = manager.register_pending_action(session_id="sess_keep", tool_name="bash", arguments={}, reason="r3")

        self.assertEqual(len(manager.get_pending_actions("sess_dc")), 2)

        # Disconnect cleanup
        cleaned = manager.cleanup_session("sess_dc", reason="client_disconnected")
        self.assertEqual(cleaned, 2)

        # sess_dc has 0 pending, while sess_keep remains untouched
        self.assertEqual(len(manager.get_pending_actions("sess_dc")), 0)
        self.assertEqual(len(manager.get_pending_actions("sess_keep")), 1)

    def test_approval_expiration_ttl(self):
        """Verifies that expired pending actions time out and cannot be approved."""
        manager = ApprovalManager()
        action_id = manager.register_pending_action(
            session_id="sess_expire",
            tool_name="bash",
            arguments={},
            reason="Expire test",
            timeout_seconds=0.05
        )
        # Wait for expiration
        asyncio.run(asyncio.sleep(0.08))

        # Attempt to approve expired action -> Rejected with expiration notice
        success, msg = manager.resolve_action(action_id, approved=True)
        self.assertFalse(success)
        self.assertIn("expired", msg.lower())

    # =========================================================================
    # 3. STREAMING REAL-TIME TOOL EVENTS
    # =========================================================================

    def test_chat_stream_emits_claw_events(self):
        """
        Verifies that /api/chat/stream streams tool events in real time
        for Claw Code workflows.
        """
        response = self.client.post(
            "/api/chat/stream",
            json={"prompt": "Find the bug in my project", "simulate": True}
        )
        self.assertEqual(response.status_code, 200)

        chunks = response.text.split("\n\n")
        events_found = set()
        done_payload = None

        for block in chunks:
            if not block.strip():
                continue
            lines = block.split("\n")
            for line in lines:
                if line.startswith("event:"):
                    events_found.add(line.split("event:")[1].strip())
                elif line.startswith("data:"):
                    try:
                        data = json.loads(line.split("data:")[1].strip())
                        if "event" in data:
                            events_found.add(data["event"])
                        if data.get("grounded_status"):
                            done_payload = data
                    except Exception:
                        pass

        self.assertIn("routing", events_found)
        self.assertIn("done", events_found)
        self.assertIsNotNone(done_payload)
        self.assertIn(done_payload.get("task_type"), ("claw_read_only", "claw_confirmation"))
        self.assertIn("grounded_status", done_payload)

    # =========================================================================
    # 4. GROUNDED COMPLETION: TEST EVIDENCE & UNCERTAINTY
    # =========================================================================

    def test_verify_test_output_evidence_truthfulness(self):
        """
        Critical Grounding Test:
        Verifies that code 0 with 0 tests or echo output is NOT marked as 'tests_passed',
        reporting uncertainty instead.
        """
        # 1. Real passing pytest
        has_ev, passed, _ = verify_test_output_evidence("=== 4 passed, 1 warning in 0.23s ===", exit_success=True)
        self.assertTrue(has_ev)
        self.assertTrue(passed)

        # 2. Empty pytest (collected 0 items) -> Must report uncertainty!
        has_ev, passed, reason = verify_test_output_evidence("collected 0 items\n=== no tests ran in 0.01s ===", exit_success=True)
        self.assertFalse(has_ev)
        self.assertIsNone(passed)
        self.assertIn("0 items", reason)

        # 3. Echo command masquerading as test -> Must report uncertainty!
        has_ev, passed, reason = verify_test_output_evidence("all tests passed successfully", exit_success=True)
        self.assertFalse(has_ev)
        self.assertIsNone(passed)

        # 4. Failed test
        has_ev, passed, _ = verify_test_output_evidence("=== 1 failed, 3 passed ===", exit_success=False)
        self.assertTrue(has_ev)
        self.assertFalse(passed)

    def test_compute_grounded_completion_states_with_evidence(self):
        """Verifies accurate distinction across all grounded completion states including unverified."""
        # 1. Proposed only
        status, passed, summary = compute_grounded_completion([], [], [])
        self.assertEqual(status, "proposed_only")
        self.assertIsNone(passed)
        self.assertIn("no workspace files were modified", summary)

        # 2. Read-only inspected
        status, passed, summary = compute_grounded_completion([], [], ["read_file", "grep_search"])
        self.assertEqual(status, "read_only_inspected")
        self.assertIsNone(passed)
        self.assertIn("read-only mode", summary)

        # 3. Files edited without tests
        status, passed, summary = compute_grounded_completion(["backend/main.py"], [], ["edit_file"])
        self.assertEqual(status, "files_edited")
        self.assertIsNone(passed)

        # 4. Tests executed with confirmed passing output
        tests_confirmed = [{"command": "pytest backend/tests", "output": "=== 5 passed in 0.1s ===", "success": True, "duration_ms": 120}]
        status, passed, summary = compute_grounded_completion(["backend/main.py"], tests_confirmed, ["edit_file", "bash"])
        self.assertEqual(status, "tests_passed")
        self.assertTrue(passed)
        self.assertIn("All tests passed", summary)

        # 5. Tests executed with code 0 but inconclusive output (Uncertainty Reported!)
        tests_inconclusive = [{"command": "pytest backend/tests", "output": "collected 0 items\nno tests ran", "success": True, "duration_ms": 50}]
        status, passed, summary = compute_grounded_completion(["backend/main.py"], tests_inconclusive, ["edit_file", "bash"])
        self.assertEqual(status, "tests_unverified")
        self.assertIsNone(passed)
        self.assertIn("unverified", summary.lower())

        # 6. Tests failed
        tests_fail = [{"command": "pytest backend/tests", "output": "=== 1 failed ===", "success": False, "duration_ms": 120}]
        status, passed, summary = compute_grounded_completion(["backend/main.py"], tests_fail, ["edit_file", "bash"])
        self.assertEqual(status, "tests_failed")
        self.assertFalse(passed)

    def test_bash_file_change_detection(self):
        """
        Verifies that detect_workspace_file_changes captures files created or modified
        by shell commands even if edit_file was never called.
        """
        # Initialize a temporary git repo in test_dir
        subprocess.run(["git", "init"], cwd=self.test_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_dir, check=True)

        # Initial commit
        init_file = Path(self.test_dir) / "README.md"
        init_file.write_text("# Initial", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.test_dir, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=self.test_dir, check=True)

        # Shell command alters README.md and creates new_script.py
        (Path(self.test_dir) / "README.md").write_text("# Modified by shell", encoding="utf-8")
        (Path(self.test_dir) / "new_script.py").write_text("print('hello')", encoding="utf-8")

        detected = asyncio.run(detect_workspace_file_changes(self.test_dir))
        self.assertIn("README.md", detected)
        self.assertIn("new_script.py", detected)

if __name__ == "__main__":
    unittest.main()
