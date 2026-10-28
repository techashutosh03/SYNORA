import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel

class PermissionDecision(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    requires_confirmation: bool = False

class PermissionEnforcer:
    """
    Security gate adapted from Claw Code's PermissionEnforcer.
    Guarantees that autonomous model tool calls cannot destroy the host machine or escape bounds.
    """

    DANGEROUS_COMMAND_PATTERNS = [
        r"\brm\s+(-rf|-fr|-r)\s+[/~]",       # rm -rf / or rm -rf ~
        r"\b(mkfs|dd\s+if=)\b",              # disk formatting
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # fork bomb
        r"\b(shutdown|reboot|halt|poweroff)\b",
        r"\bchmod\s+(-R\s+)?777\s+[/~]",
        r">>\s*/dev/sd[a-z]",                # writing directly to disk device
    ]

    READ_ONLY_TOOLS = {"read_file", "list_dir", "grep_search", "glob_files"}

    def __init__(self, mode: str = "autonomous", workspace_root: Optional[str] = None):
        """
        mode:
          - 'autonomous': Auto-approves safe tools, blocks explicitly dangerous commands.
          - 'ask': Flags writes and bash commands as requiring explicit confirmation.
          - 'read_only': Rejects all write and bash execution operations.
        """
        self.mode = mode
        self.workspace_root = Path(workspace_root or ".").resolve()

    def set_mode(self, mode: str):
        if mode in ("autonomous", "ask", "read_only"):
            self.mode = mode

    def check_tool_permission(self, tool_name: str, arguments: Dict[str, Any]) -> PermissionDecision:
        name = tool_name.lower().strip()

        # 1. Read-only enforcement
        if self.mode == "read_only":
            if name not in self.READ_ONLY_TOOLS:
                return PermissionDecision(
                    allowed=False,
                    reason=f"Permission denied: Agent is operating in 'read_only' mode. Tool '{tool_name}' cannot be executed."
                )

        # 2. Bash command safety checks
        if name == "bash":
            command = arguments.get("command", "")
            for pattern in self.DANGEROUS_COMMAND_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return PermissionDecision(
                        allowed=False,
                        reason=f"Security Gate: Blocked potentially destructive command matching pattern '{pattern}'."
                    )

            if self.mode == "ask":
                return PermissionDecision(
                    allowed=True,
                    requires_confirmation=True,
                    reason=f"Shell execution '{command}' requires user confirmation in 'ask' mode."
                )

        # 3. File write checks
        if name in ("write_file", "edit_file"):
            path_str = arguments.get("path", "")
            if not path_str:
                return PermissionDecision(allowed=False, reason="Missing file path argument.")

            resolved = Path(path_str)
            if not resolved.is_absolute():
                resolved = (self.workspace_root / resolved).resolve()

            # Prevent writing to critical system directories
            forbidden_roots = ["/System", "/etc", "/usr/bin", "/bin", "/sbin", "/private"]
            for f_root in forbidden_roots:
                if str(resolved).startswith(f_root):
                    return PermissionDecision(
                        allowed=False,
                        reason=f"Security Gate: Cannot modify protected system path {resolved}."
                    )

            if self.mode == "ask":
                return PermissionDecision(
                    allowed=True,
                    requires_confirmation=True,
                    reason=f"File modification on '{path_str}' requires user confirmation in 'ask' mode."
                )

        return PermissionDecision(allowed=True)

permission_enforcer = PermissionEnforcer()
