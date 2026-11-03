import re
import os
import contextvars
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from pydantic import BaseModel

# Request / task scoped permission mode via ContextVar (prevents global state clobbering across concurrent tasks)
# Strict security default: 'ask' (human confirmation required for mutating operations)
_current_permission_mode: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_current_permission_mode", default="ask"
)

# Permission strictness hierarchy: higher number = stricter policy
MODE_STRICTNESS = {
    "read_only": 3,
    "ask": 2,
    "autonomous": 1
}

def cap_permission_mode(configured_mode: str, requested_override: Optional[str]) -> str:
    """
    Enforces permission monotonicity.
    A manual override or client parameter may only INCREASE or MAINTAIN strictness,
    never loosen permissions beyond the server/system configured baseline.
    
    Examples:
    - configured 'read_only' + override 'mutate' -> 'read_only' (override cannot elevate)
    - configured 'ask' + override 'autonomous' -> 'ask' (cannot bypass confirmation)
    - configured 'ask' + override 'read_only' -> 'read_only' (tightening is allowed)
    - configured 'autonomous' + override 'ask' -> 'ask' (tightening is allowed)
    """
    conf = (configured_mode or "ask").lower().strip()
    if not requested_override:
        return conf

    req = requested_override.lower().strip()
    # Normalize aliases
    if req in ("mutate", "write", "edit"):
        req = "ask"
    elif req in ("inspect", "audit", "search"):
        req = "read_only"

    if req not in MODE_STRICTNESS:
        return conf

    conf_level = MODE_STRICTNESS.get(conf, 2)
    req_level = MODE_STRICTNESS.get(req, 2)

    # Effective mode must be the maximum strictness between configured and requested
    max_level = max(conf_level, req_level)
    for mode_name, lvl in MODE_STRICTNESS.items():
        if lvl == max_level:
            return mode_name
    return conf

@contextmanager
def permission_scope(mode: str):
    """Context manager to isolate permission modes to a specific request, session, or coroutine."""
    token = _current_permission_mode.set(mode)
    try:
        yield
    finally:
        _current_permission_mode.reset(token)

class PermissionDecision(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    requires_confirmation: bool = False

class PermissionEnforcer:
    """
    Security gate adapted from Claw Code's PermissionEnforcer.
    Guarantees that autonomous model tool calls cannot destroy the host machine,
    escape workspace boundaries via symlinks or directory traversal, exfiltrate credentials,
    or bypass system safety permissions.
    """

    DANGEROUS_COMMAND_PATTERNS = [
        # System destruction & formatting
        r"\brm\s+(-rf|-fr|-r)\s+[/~]",                # rm -rf / or rm -rf ~
        r"\b(mkfs|dd\s+if=)\b",                       # disk formatting
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # fork bomb
        r"\b(shutdown|reboot|halt|poweroff)\b",       # machine power state
        r"\bchmod\s+(-R\s+)?777\s+[/~]",              # mass permission open
        r">>\s*/dev/sd[a-z]",                         # writing directly to disk device

        # Privilege escalation
        r"\b(sudo|su|doas|pkexec)\b",

        # Network pipe to shell execution (remote code injection / download-and-exec)
        r"\b(curl|wget|fetch)\b.*\|\s*(ba|z)?sh\b",
        r"\bpython[0-9.]*\s+-c\s+.*urllib",

        # Network reverse shells / backdoors
        r"\b(nc|netcat|ncat)\b.*(-e|/bin/(ba)?sh)",
        r"\bbash\s+-i\s+>&",
        r"\b/dev/tcp/",

        # Shell credential inspection & exfiltration
        r"\b(cat|head|tail|less|more|grep|strings|od|xxd|hexdump)\s+.*(?:~|\$HOME|/home/\w+|/Users/\w+)/\.(ssh|aws|gnupg|netrc|bash_history|zsh_history)\b",
        r"\b(cat|head|tail|less|more|grep)\s+.*(/etc/shadow|/etc/sudoers|/private/etc/shadow)\b",

        # Shell environment credential exfiltration
        r"\b(env|printenv|export)\b.*\|\s*(curl|wget|nc|netcat)\b",
    ]

    READ_ONLY_TOOLS = {"read_file", "list_dir", "grep_search", "glob_files", "git_status", "git_diff"}

    SENSITIVE_SYSTEM_PREFIXES = (
        "/etc",
        "/private/etc",
        "/proc",
        "/sys",
        "/dev",
        "/var/run",
        "/System",
        "/usr/bin",
        "/bin",
        "/sbin",
        "/Library/SystemExtensions",
    )

    SENSITIVE_FILENAME_PATTERNS = [
        r"^id_rsa(\.pub)?$",
        r"^id_ed25519(\.pub)?$",
        r"^id_ecdsa(\.pub)?$",
        r"^\.bash_history$",
        r"^\.zsh_history$",
        r"^\.netrc$",
        r"^credentials(\.json)?$",
        r"^service_account.*\.json$",
    ]

    def __init__(self, mode: str = "ask", workspace_root: Optional[str] = None):
        """
        mode:
          - 'ask': (Default) Flags file writes and bash commands as requiring explicit confirmation.
          - 'read_only': Rejects all write and bash execution operations.
          - 'autonomous': Auto-approves safe tools, blocks explicitly dangerous commands.
        """
        self.workspace_root = Path(workspace_root or ".").resolve()
        _current_permission_mode.set(mode)

    @property
    def mode(self) -> str:
        return _current_permission_mode.get()

    @mode.setter
    def mode(self, val: str):
        if val in ("autonomous", "ask", "read_only"):
            _current_permission_mode.set(val)

    def set_mode(self, mode: str):
        self.mode = mode

    def _is_within_workspace(self, target_path: Path) -> bool:
        """
        Validates whether target_path (once fully resolved of any symlinks or ..)
        lives strictly inside the designated workspace_root.
        """
        try:
            resolved_target = target_path.resolve()
            resolved_ws = self.workspace_root.resolve()
            return resolved_target.is_relative_to(resolved_ws)
        except (ValueError, RuntimeError):
            return False

    def is_sensitive_path(self, target_path: Path) -> Tuple[bool, str]:
        """
        Checks whether target_path points to system security files or user credentials,
        preventing directory traversal and symlink escapes across both read and write tools.
        """
        try:
            resolved = target_path.resolve()
            resolved_str = str(resolved)

            # 1. Sensitive system directories
            for prefix in self.SENSITIVE_SYSTEM_PREFIXES:
                if resolved_str == prefix or resolved_str.startswith(prefix + "/"):
                    return True, f"System security path: {resolved_str}"

            # 2. Sensitive user dotfiles in user home directory (~/.ssh, ~/.aws, ~/.gnupg, etc.)
            home = str(Path.home().resolve())
            if resolved_str.startswith(home):
                rel_to_home = resolved_str[len(home):].lstrip("/")
                sensitive_dirs = (".ssh", ".aws", ".gnupg", ".config/gcloud", ".netrc")
                for sdir in sensitive_dirs:
                    if rel_to_home == sdir or rel_to_home.startswith(sdir + "/"):
                        return True, f"User credentials path: ~/{rel_to_home}"

            # 3. Sensitive file names
            fname = resolved.name
            for pat in self.SENSITIVE_FILENAME_PATTERNS:
                if re.search(pat, fname, re.IGNORECASE):
                    return True, f"Sensitive credential file: {fname}"

            return False, ""
        except Exception as e:
            return True, f"Path resolution error: {str(e)}"

    def check_tool_permission(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        mode: Optional[str] = None
    ) -> PermissionDecision:
        effective_mode = mode or self.mode
        name = tool_name.lower().strip()

        # 1. Read-only enforcement
        if effective_mode == "read_only":
            if name not in self.READ_ONLY_TOOLS:
                return PermissionDecision(
                    allowed=False,
                    reason=f"Permission denied: Agent is operating in 'read_only' mode. Tool '{tool_name}' cannot be executed."
                )

        # 2. Sensitive security files strictly forbidden from access across all modes and tools (read or write)
        path_str = arguments.get("path", "")
        if path_str and name in ("read_file", "write_file", "edit_file", "list_dir", "grep_search", "glob_files"):
            target = Path(path_str)
            if not target.is_absolute():
                target = self.workspace_root / target

            is_sensitive, sensitive_reason = self.is_sensitive_path(target)
            if is_sensitive:
                return PermissionDecision(
                    allowed=False,
                    reason=f"Security Gate: Access to sensitive path is strictly blocked in all modes ({sensitive_reason})."
                )

        # 3. Workspace boundary checks for mutating tools (write_file, edit_file)
        if name in ("write_file", "edit_file"):
            if not path_str:
                return PermissionDecision(allowed=False, reason="Missing file path argument.")

            target = Path(path_str)
            if not target.is_absolute():
                target = self.workspace_root / target

            # Enforce workspace containment (catches symlink escapes and ../ path traversal)
            if not self._is_within_workspace(target):
                return PermissionDecision(
                    allowed=False,
                    reason=f"Security Gate: Writing outside workspace boundary is strictly forbidden (target: '{target.resolve()}', workspace: '{self.workspace_root}'). Symlink escapes and directory traversals are blocked."
                )

            if effective_mode == "ask":
                return PermissionDecision(
                    allowed=True,
                    requires_confirmation=True,
                    reason=f"File modification on '{path_str}' requires user confirmation in 'ask' mode."
                )

        # 4. Bash command safety checks
        if name == "bash":
            command = arguments.get("command", "")
            for pattern in self.DANGEROUS_COMMAND_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return PermissionDecision(
                        allowed=False,
                        reason=f"Security Gate: Blocked potentially destructive or unauthorized command matching pattern '{pattern}'."
                    )

            if effective_mode == "ask":
                return PermissionDecision(
                    allowed=True,
                    requires_confirmation=True,
                    reason=f"Shell execution '{command}' requires user confirmation in 'ask' mode."
                )

        return PermissionDecision(allowed=True)

permission_enforcer = PermissionEnforcer()
