import os
import sys
import time
import glob
import re
import asyncio
import subprocess
import json
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class ToolManager:
    """
    Claw Code Native Tool Engine integrated directly into SYNORA.
    Provides fast, safe, local execution of filesystem, terminal, git, and search operations.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()

    def set_workspace_root(self, path: str):
        self.workspace_root = Path(path).resolve()

    def _resolve_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            p = (self.workspace_root / p).resolve()
        return p

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns standard JSON schemas compatible with Ollama and OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Execute a shell command in the workspace terminal with timeout and output capture.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The exact shell command to run (e.g. 'npm test', 'git status', 'ls -la')."
                            },
                            "timeout_seconds": {
                                "type": "integer",
                                "description": "Maximum execution time in seconds before terminating (default 60).",
                                "default": 60
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file with line numbers. Optionally slice by line range.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative or absolute path to the file."
                            },
                            "start_line": {
                                "type": "integer",
                                "description": "Optional starting line number (1-based, inclusive)."
                            },
                            "end_line": {
                                "type": "integer",
                                "description": "Optional ending line number (1-based, inclusive)."
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create a new file or completely overwrite an existing file with the specified content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative or absolute path to the file to create or overwrite."
                            },
                            "content": {
                                "type": "string",
                                "description": "The complete raw text content to write into the file."
                            }
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Perform precise, surgical replacements of text blocks inside a file without overwriting the entire file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative or absolute path to the file to edit."
                            },
                            "old_string": {
                                "type": "string",
                                "description": "Exact text block currently in the file to be replaced."
                            },
                            "new_string": {
                                "type": "string",
                                "description": "Exact replacement text block to put in place of old_string."
                            }
                        },
                        "required": ["path", "old_string", "new_string"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "grep_search",
                    "description": "Search for code patterns, function definitions, or strings across the workspace using ripgrep or regex.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search term or regular expression to look for."
                            },
                            "path": {
                                "type": "string",
                                "description": "Directory or file to limit search to (default '.').",
                                "default": "."
                            },
                            "is_regex": {
                                "type": "boolean",
                                "description": "Whether query should be treated as regex pattern.",
                                "default": False
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "glob_files",
                    "description": "Find files matching wildcard pattern across directory hierarchy (e.g. '**/*.py', 'src/**/*.rs').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to match."
                            },
                            "path": {
                                "type": "string",
                                "description": "Base directory to search from (default '.').",
                                "default": "."
                            }
                        },
                        "required": ["pattern"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "List directory contents with file size and type annotations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path to list (default '.').",
                                "default": "."
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to list recursively.",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Check git repository status: branch name, uncommitted changes, untracked files.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "View git diff of unstaged or staged modifications in the workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Optional file path to limit diff inspection to."
                            },
                            "staged": {
                                "type": "boolean",
                                "description": "Whether to view staged changes (--cached).",
                                "default": False
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "git_commit",
                    "description": "Commit changes to git with a clear, concise commit message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Commit message explaining the changes."
                            },
                            "stage_all": {
                                "type": "boolean",
                                "description": "Whether to automatically stage all changes (git add -A) before committing.",
                                "default": True
                            }
                        },
                        "required": ["message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_fetch",
                    "description": "Fetch content of an external web page or documentation URL via HTTP GET.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The full HTTP or HTTPS URL to fetch."
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "todo_write",
                    "description": "Update or create a task checklist (.claw/todos.json) to plan and track multi-step execution.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "todos": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "task": {"type": "string"},
                                        "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "failed"]}
                                    },
                                    "required": ["task", "status"]
                                },
                                "description": "List of task items."
                            }
                        },
                        "required": ["todos"]
                    }
                }
            }
        ]

    # --- Tool Implementations ---

    async def execute_bash(self, command: str, timeout_seconds: int = 60) -> ToolResult:
        start_time = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=float(timeout_seconds)
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return ToolResult(
                    tool_name="bash",
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout_seconds} seconds: {command}",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            stdout_str = stdout_data.decode("utf-8", errors="replace")
            stderr_str = stderr_data.decode("utf-8", errors="replace")
            exit_code = proc.returncode

            duration_ms = (time.perf_counter() - start_time) * 1000
            combined_output = stdout_str
            if stderr_str:
                if combined_output:
                    combined_output += "\n[stderr]\n" + stderr_str
                else:
                    combined_output = stderr_str

            return ToolResult(
                tool_name="bash",
                success=(exit_code == 0),
                output=combined_output,
                error=None if exit_code == 0 else f"Process exited with code {exit_code}",
                duration_ms=duration_ms,
                metadata={"exit_code": exit_code, "command": command}
            )

        except Exception as e:
            return ToolResult(
                tool_name="bash",
                success=False,
                output="",
                error=f"Execution failed: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_read_file(
        self,
        path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> ToolResult:
        start_time = time.perf_counter()
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return ToolResult(
                    tool_name="read_file",
                    success=False,
                    output="",
                    error=f"File not found: {path} (resolved to {file_path})",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            if file_path.is_dir():
                return ToolResult(
                    tool_name="read_file",
                    success=False,
                    output="",
                    error=f"Target path is a directory, not a file: {path}",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            s_idx = max(0, (start_line - 1)) if start_line is not None else 0
            e_idx = min(len(lines), end_line) if end_line is not None else len(lines)

            selected_lines = lines[s_idx:e_idx]
            numbered = [f"{i + 1 + s_idx:4d} | {line}" for i, line in enumerate(selected_lines)]
            output_str = "\n".join(numbered)

            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="read_file",
                success=True,
                output=output_str,
                duration_ms=duration_ms,
                metadata={
                    "total_lines": len(lines),
                    "sliced_from": s_idx + 1,
                    "sliced_to": e_idx
                }
            )
        except Exception as e:
            return ToolResult(
                tool_name="read_file",
                success=False,
                output="",
                error=f"Failed to read file {path}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_write_file(self, path: str, content: str) -> ToolResult:
        start_time = time.perf_counter()
        try:
            file_path = self._resolve_path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="write_file",
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                duration_ms=duration_ms,
                metadata={"bytes_written": len(content.encode('utf-8'))}
            )
        except Exception as e:
            return ToolResult(
                tool_name="write_file",
                success=False,
                output="",
                error=f"Failed to write file {path}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_edit_file(self, path: str, old_string: str, new_string: str) -> ToolResult:
        start_time = time.perf_counter()
        try:
            file_path = self._resolve_path(path)
            if not file_path.exists():
                return ToolResult(
                    tool_name="edit_file",
                    success=False,
                    output="",
                    error=f"File not found: {path}",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            content = file_path.read_text(encoding="utf-8")
            if old_string not in content:
                return ToolResult(
                    tool_name="edit_file",
                    success=False,
                    output="",
                    error=f"The text block specified in 'old_string' was not found in {path}. Make sure whitespace and line breaks match exactly.",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            count = content.count(old_string)
            if count > 1:
                return ToolResult(
                    tool_name="edit_file",
                    success=False,
                    output="",
                    error=f"Found {count} occurrences of 'old_string' in {path}. Please provide a larger unique surrounding block of code.",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            new_content = content.replace(old_string, new_string, 1)
            file_path.write_text(new_content, encoding="utf-8")

            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="edit_file",
                success=True,
                output=f"Successfully updated {path} (replaced target block)",
                duration_ms=duration_ms,
                metadata={"replacements": 1}
            )
        except Exception as e:
            return ToolResult(
                tool_name="edit_file",
                success=False,
                output="",
                error=f"Failed to edit file {path}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_grep_search(
        self,
        query: str,
        path: str = ".",
        is_regex: bool = False
    ) -> ToolResult:
        start_time = time.perf_counter()
        try:
            target_path = self._resolve_path(path)
            results = []

            has_rg = subprocess.run(["which", "rg"], capture_output=True).returncode == 0
            if has_rg:
                cmd = ["rg", "--line-number", "--max-count", "50", query, str(target_path)]
                if not is_regex:
                    cmd.insert(1, "-F")
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                out_text = stdout.decode("utf-8", errors="replace")
                duration_ms = (time.perf_counter() - start_time) * 1000
                return ToolResult(
                    tool_name="grep_search",
                    success=True,
                    output=out_text or "No matches found.",
                    duration_ms=duration_ms,
                    metadata={"query": query, "engine": "ripgrep"}
                )

            pattern = re.compile(query if is_regex else re.escape(query))
            match_count = 0
            for root, dirs, files in os.walk(target_path):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "target", "venv", "__pycache__")]
                for f in files:
                    if f.startswith("."):
                        continue
                    full_p = Path(root) / f
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as fh:
                            for idx, line in enumerate(fh, 1):
                                if pattern.search(line):
                                    rel = full_p.relative_to(self.workspace_root)
                                    results.append(f"{rel}:{idx}: {line.strip()}")
                                    match_count += 1
                                    if match_count >= 50:
                                        break
                    except Exception:
                        continue
                    if match_count >= 50:
                        break
                if match_count >= 50:
                    break

            duration_ms = (time.perf_counter() - start_time) * 1000
            out_str = "\n".join(results) if results else "No matches found."
            return ToolResult(
                tool_name="grep_search",
                success=True,
                output=out_str,
                duration_ms=duration_ms,
                metadata={"matches": len(results), "engine": "python"}
            )
        except Exception as e:
            return ToolResult(
                tool_name="grep_search",
                success=False,
                output="",
                error=f"Grep search failed: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_glob_files(self, pattern: str, path: str = ".") -> ToolResult:
        start_time = time.perf_counter()
        try:
            base_dir = self._resolve_path(path)
            full_pattern = str(base_dir / pattern)
            matches = glob.glob(full_pattern, recursive=True)

            rel_matches = []
            for m in sorted(matches)[:100]:
                try:
                    rel_matches.append(str(Path(m).relative_to(self.workspace_root)))
                except ValueError:
                    rel_matches.append(m)

            duration_ms = (time.perf_counter() - start_time) * 1000
            output_str = "\n".join(rel_matches) if rel_matches else f"No files matched pattern '{pattern}'"
            return ToolResult(
                tool_name="glob_files",
                success=True,
                output=output_str,
                duration_ms=duration_ms,
                metadata={"count": len(rel_matches)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="glob_files",
                success=False,
                output="",
                error=f"Glob search failed: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_list_dir(self, path: str = ".", recursive: bool = False) -> ToolResult:
        start_time = time.perf_counter()
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return ToolResult(
                    tool_name="list_dir",
                    success=False,
                    output="",
                    error=f"Directory does not exist: {path}",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            entries = []
            if recursive:
                for root, dirs, files in os.walk(dir_path):
                    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "target", "venv", "__pycache__")]
                    rel_root = Path(root).relative_to(self.workspace_root)
                    for f in files:
                        if not f.startswith("."):
                            entries.append(str(rel_root / f))
            else:
                for item in sorted(os.listdir(dir_path)):
                    if item.startswith("."):
                        continue
                    item_path = dir_path / item
                    if item_path.is_dir():
                        entries.append(f"[DIR]  {item}/")
                    else:
                        size_kb = round(item_path.stat().st_size / 1024, 1)
                        entries.append(f"[FILE] {item} ({size_kb} KB)")

            duration_ms = (time.perf_counter() - start_time) * 1000
            output_str = f"Contents of {path} ({len(entries)} items):\n" + "\n".join(entries)
            return ToolResult(
                tool_name="list_dir",
                success=True,
                output=output_str,
                duration_ms=duration_ms,
                metadata={"item_count": len(entries)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="list_dir",
                success=False,
                output="",
                error=f"Error listing directory {path}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_git_status(self) -> ToolResult:
        start_time = time.perf_counter()
        try:
            cmd = ["git", "status", "--short", "--branch"]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            duration_ms = (time.perf_counter() - start_time) * 1000
            if proc.returncode == 0:
                output = stdout.decode("utf-8", errors="replace").strip() or "Clean working tree (nothing to commit)."
                return ToolResult(tool_name="git_status", success=True, output=output, duration_ms=duration_ms)
            else:
                return ToolResult(tool_name="git_status", success=False, output="", error=stderr.decode("utf-8", errors="replace"), duration_ms=duration_ms)
        except Exception as e:
            return ToolResult(tool_name="git_status", success=False, output="", error=f"Git status failed: {str(e)}", duration_ms=(time.perf_counter() - start_time) * 1000)

    async def execute_git_diff(self, path: Optional[str] = None, staged: bool = False) -> ToolResult:
        start_time = time.perf_counter()
        try:
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--cached")
            if path:
                cmd.extend(["--", path])
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            duration_ms = (time.perf_counter() - start_time) * 1000
            if proc.returncode == 0:
                diff_text = stdout.decode("utf-8", errors="replace").strip() or "No uncommitted diffs found."
                return ToolResult(tool_name="git_diff", success=True, output=diff_text, duration_ms=duration_ms)
            else:
                return ToolResult(tool_name="git_diff", success=False, output="", error=stderr.decode("utf-8", errors="replace"), duration_ms=duration_ms)
        except Exception as e:
            return ToolResult(tool_name="git_diff", success=False, output="", error=f"Git diff failed: {str(e)}", duration_ms=(time.perf_counter() - start_time) * 1000)

    async def execute_git_commit(self, message: str, stage_all: bool = True) -> ToolResult:
        start_time = time.perf_counter()
        if not message.strip():
            return ToolResult(tool_name="git_commit", success=False, output="", error="Commit message cannot be empty.")
        try:
            if stage_all:
                add_proc = await asyncio.create_subprocess_exec("git", "add", "-A", cwd=str(self.workspace_root))
                await add_proc.wait()

            commit_proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", message.strip(),
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await commit_proc.communicate()
            duration_ms = (time.perf_counter() - start_time) * 1000
            if commit_proc.returncode == 0:
                return ToolResult(tool_name="git_commit", success=True, output=stdout.decode("utf-8", errors="replace"), duration_ms=duration_ms)
            else:
                return ToolResult(tool_name="git_commit", success=False, output="", error=stderr.decode("utf-8", errors="replace"), duration_ms=duration_ms)
        except Exception as e:
            return ToolResult(tool_name="git_commit", success=False, output="", error=f"Git commit failed: {str(e)}", duration_ms=(time.perf_counter() - start_time) * 1000)

    async def execute_web_fetch(self, url: str) -> ToolResult:
        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                res = await client.get(url, headers={"User-Agent": "SYNORA-Claw/1.0"})
                if res.status_code >= 400:
                    return ToolResult(
                        tool_name="web_fetch",
                        success=False,
                        output="",
                        error=f"HTTP {res.status_code} while fetching {url}",
                        duration_ms=(time.perf_counter() - start_time) * 1000
                    )
                text = res.text
                if "<html" in text.lower():
                    text = re.sub(r"<script.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r"<style.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = re.sub(r"\s+", " ", text).strip()
                preview = text[:8000]
                duration_ms = (time.perf_counter() - start_time) * 1000
                return ToolResult(
                    tool_name="web_fetch",
                    success=True,
                    output=preview,
                    duration_ms=duration_ms,
                    metadata={"url": url, "chars": len(preview)}
                )
        except Exception as e:
            return ToolResult(
                tool_name="web_fetch",
                success=False,
                output="",
                error=f"Web fetch failed for {url}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_todo_write(self, todos: List[Dict[str, Any]]) -> ToolResult:
        start_time = time.perf_counter()
        try:
            todo_dir = self.workspace_root / ".claw"
            todo_dir.mkdir(parents=True, exist_ok=True)
            todo_path = todo_dir / "todos.json"
            todo_path.write_text(json.dumps(todos, indent=2), encoding="utf-8")
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="todo_write",
                success=True,
                output=f"Successfully updated task list ({len(todos)} items saved to .claw/todos.json)",
                duration_ms=duration_ms,
                metadata={"count": len(todos)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="todo_write",
                success=False,
                output="",
                error=f"Failed to write todo items: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Central tool dispatcher."""
        name = tool_name.lower().strip()
        if name == "bash":
            return await self.execute_bash(
                command=arguments.get("command", ""),
                timeout_seconds=arguments.get("timeout_seconds", 60)
            )
        elif name == "read_file":
            return await self.execute_read_file(
                path=arguments.get("path", ""),
                start_line=arguments.get("start_line"),
                end_line=arguments.get("end_line")
            )
        elif name == "write_file":
            return await self.execute_write_file(
                path=arguments.get("path", ""),
                content=arguments.get("content", "")
            )
        elif name == "edit_file":
            return await self.execute_edit_file(
                path=arguments.get("path", ""),
                old_string=arguments.get("old_string", ""),
                new_string=arguments.get("new_string", "")
            )
        elif name == "grep_search":
            return await self.execute_grep_search(
                query=arguments.get("query", ""),
                path=arguments.get("path", "."),
                is_regex=arguments.get("is_regex", False)
            )
        elif name == "glob_files":
            return await self.execute_glob_files(
                pattern=arguments.get("pattern", "*"),
                path=arguments.get("path", ".")
            )
        elif name == "list_dir":
            return await self.execute_list_dir(
                path=arguments.get("path", "."),
                recursive=arguments.get("recursive", False)
            )
        elif name in ("git_status", "status"):
            return await self.execute_git_status()
        elif name in ("git_diff", "diff"):
            return await self.execute_git_diff(
                path=arguments.get("path"),
                staged=arguments.get("staged", False)
            )
        elif name in ("git_commit", "commit"):
            return await self.execute_git_commit(
                message=arguments.get("message", ""),
                stage_all=arguments.get("stage_all", True)
            )
        elif name in ("web_fetch", "fetch"):
            return await self.execute_web_fetch(url=arguments.get("url", ""))
        elif name in ("todo_write", "todos"):
            return await self.execute_todo_write(todos=arguments.get("todos", []))
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output="",
                error=f"Unknown tool '{tool_name}'. Available tools: bash, read_file, write_file, edit_file, grep_search, glob_files, list_dir, git_status, git_diff, git_commit, web_fetch, todo_write."
            )

tool_manager = ToolManager()
