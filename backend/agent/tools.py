import os
import sys
import time
import glob
import re
import asyncio
import subprocess
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
    Provides fast, safe, local execution of filesystem, terminal, and search operations.
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
                    "description": "Write or overwrite a file with given content. Creates parent directories automatically.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative or absolute path to the file."
                            },
                            "content": {
                                "type": "string",
                                "description": "Complete text content to write."
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
                    "description": "Surgically replace an exact unique string match in a file with new replacement string.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Path to the file to edit."
                            },
                            "old_string": {
                                "type": "string",
                                "description": "Exact text substring currently in the file that needs to be replaced."
                            },
                            "new_string": {
                                "type": "string",
                                "description": "Exact replacement text to substitute in."
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
                    "description": "Search file contents across the workspace using regex or literal text matching.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text or regex pattern to search for."
                            },
                            "path": {
                                "type": "string",
                                "description": "Directory or file path to search within (default current workspace).",
                                "default": "."
                            },
                            "is_regex": {
                                "type": "boolean",
                                "description": "True if query is a regular expression, False for literal matching.",
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
                    "description": "Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.jsx').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Glob pattern to match file names."
                            },
                            "path": {
                                "type": "string",
                                "description": "Base directory to start search from (default workspace root).",
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
                    "description": "List files and subdirectories in a directory with file sizes and type markers.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory to list (default '.').",
                                "default": "."
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to list subdirectories recursively.",
                                "default": False
                            }
                        }
                    }
                }
            }
        ]

    # --- Tool Implementations ---

    async def execute_bash(self, command: str, timeout_seconds: int = 60) -> ToolResult:
        start_time = time.perf_counter()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(), timeout=timeout_seconds
                )
                stdout = stdout_data.decode(errors="replace").strip()
                stderr = stderr_data.decode(errors="replace").strip()
                exit_code = process.returncode
                duration_ms = (time.perf_counter() - start_time) * 1000

                combined = []
                if stdout:
                    combined.append(stdout)
                if stderr:
                    combined.append(f"[STDERR]\n{stderr}")
                output_str = "\n".join(combined) if combined else "(Command exited with no output)"

                return ToolResult(
                    tool_name="bash",
                    success=(exit_code == 0),
                    output=output_str,
                    error=stderr if exit_code != 0 else None,
                    duration_ms=duration_ms,
                    metadata={"exit_code": exit_code, "command": command}
                )
            except asyncio.TimeoutError:
                process.kill()
                duration_ms = (time.perf_counter() - start_time) * 1000
                return ToolResult(
                    tool_name="bash",
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout_seconds} seconds.",
                    duration_ms=duration_ms,
                    metadata={"command": command, "timed_out": True}
                )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="bash",
                success=False,
                output="",
                error=f"Failed to execute bash command: {str(e)}",
                duration_ms=duration_ms
            )

    async def execute_read_file(
        self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> ToolResult:
        start_time = time.perf_counter()
        file_path = self._resolve_path(path)

        if not file_path.exists():
            return ToolResult(
                tool_name="read_file",
                success=False,
                output="",
                error=f"File not found: {path}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )
        if file_path.is_dir():
            return ToolResult(
                tool_name="read_file",
                success=False,
                output="",
                error=f"Path is a directory, not a file: {path}. Use list_dir instead.",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_idx = max(0, (start_line - 1)) if start_line is not None else 0
            e_idx = min(total_lines, end_line) if end_line is not None else total_lines

            sliced = lines[s_idx:e_idx]
            formatted_lines = [
                f"{idx + 1:4d} | {line.rstrip()}"
                for idx, line in enumerate(sliced, start=s_idx)
            ]
            content_str = "\n".join(formatted_lines)
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ToolResult(
                tool_name="read_file",
                success=True,
                output=content_str,
                duration_ms=duration_ms,
                metadata={"total_lines": total_lines, "returned_lines": len(sliced), "path": str(file_path)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="read_file",
                success=False,
                output="",
                error=f"Error reading {path}: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_write_file(self, path: str, content: str) -> ToolResult:
        start_time = time.perf_counter()
        file_path = self._resolve_path(path)

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            duration_ms = (time.perf_counter() - start_time) * 1000
            bytes_written = len(content.encode("utf-8"))
            return ToolResult(
                tool_name="write_file",
                success=True,
                output=f"Successfully wrote {bytes_written} bytes to {path}.",
                duration_ms=duration_ms,
                metadata={"bytes_written": bytes_written, "path": str(file_path)}
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
        file_path = self._resolve_path(path)

        if not file_path.exists():
            return ToolResult(
                tool_name="edit_file",
                success=False,
                output="",
                error=f"Cannot edit non-existent file: {path}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            occurrences = content.count(old_string)
            if occurrences == 0:
                return ToolResult(
                    tool_name="edit_file",
                    success=False,
                    output="",
                    error=f"Target string not found in {path}. Make sure whitespace and indentation match exactly.",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )
            if occurrences > 1:
                return ToolResult(
                    tool_name="edit_file",
                    success=False,
                    output="",
                    error=f"Target string found {occurrences} times in {path}. Must be unique. Add surrounding context lines.",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

            updated = content.replace(old_string, new_string, 1)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(updated)

            duration_ms = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                tool_name="edit_file",
                success=True,
                output=f"Successfully updated {path} (1 substitution performed).",
                duration_ms=duration_ms,
                metadata={"path": str(file_path), "replacements": 1}
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
        self, query: str, path: str = ".", is_regex: bool = False
    ) -> ToolResult:
        start_time = time.perf_counter()
        search_root = self._resolve_path(path)

        if not search_root.exists():
            return ToolResult(
                tool_name="grep_search",
                success=False,
                output="",
                error=f"Search path does not exist: {path}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

        matches = []
        pattern = None
        if is_regex:
            try:
                pattern = re.compile(query)
            except re.error as e:
                return ToolResult(
                    tool_name="grep_search",
                    success=False,
                    output="",
                    error=f"Invalid regex: {str(e)}",
                    duration_ms=(time.perf_counter() - start_time) * 1000
                )

        # Walk directory
        ignored_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist", "build"}
        count = 0
        max_matches = 100

        try:
            for root, dirs, files in os.walk(search_root):
                dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
                for file_name in files:
                    if file_name.startswith("."):
                        continue
                    full_p = Path(root) / file_name
                    # Skip large binary files
                    if full_p.stat().st_size > 1024 * 1024 * 2:  # > 2MB
                        continue
                    try:
                        with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                line_clean = line.rstrip()
                                hit = False
                                if is_regex and pattern:
                                    if pattern.search(line_clean):
                                        hit = True
                                elif query.lower() in line_clean.lower():
                                    hit = True

                                if hit:
                                    rel_path = full_p.relative_to(self.workspace_root)
                                    matches.append(f"{rel_path}:{line_num}: {line_clean}")
                                    count += 1
                                    if count >= max_matches:
                                        break
                    except Exception:
                        continue
                    if count >= max_matches:
                        break
                if count >= max_matches:
                    break

            duration_ms = (time.perf_counter() - start_time) * 1000
            if not matches:
                return ToolResult(
                    tool_name="grep_search",
                    success=True,
                    output=f"No matches found for '{query}' in {path}.",
                    duration_ms=duration_ms
                )
            
            summary = f"Found {len(matches)} match(es):\n" + "\n".join(matches)
            return ToolResult(
                tool_name="grep_search",
                success=True,
                output=summary,
                duration_ms=duration_ms,
                metadata={"matches_count": len(matches)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="grep_search",
                success=False,
                output="",
                error=f"Grep search error: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_glob_files(self, pattern: str, path: str = ".") -> ToolResult:
        start_time = time.perf_counter()
        base = self._resolve_path(path)
        try:
            matched_paths = list(base.glob(pattern))
            rel_paths = []
            for p in matched_paths:
                if any(part in {".git", "node_modules", "__pycache__", "venv"} for part in p.parts):
                    continue
                try:
                    rel_paths.append(str(p.relative_to(self.workspace_root)))
                except ValueError:
                    rel_paths.append(str(p))

            rel_paths = sorted(rel_paths)[:150]
            duration_ms = (time.perf_counter() - start_time) * 1000

            if not rel_paths:
                return ToolResult(
                    tool_name="glob_files",
                    success=True,
                    output=f"No files matched pattern '{pattern}'.",
                    duration_ms=duration_ms
                )

            output_str = f"Matched {len(rel_paths)} file(s):\n" + "\n".join(rel_paths)
            return ToolResult(
                tool_name="glob_files",
                success=True,
                output=output_str,
                duration_ms=duration_ms,
                metadata={"matched_count": len(rel_paths)}
            )
        except Exception as e:
            return ToolResult(
                tool_name="glob_files",
                success=False,
                output="",
                error=f"Glob error: {str(e)}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

    async def execute_list_dir(self, path: str = ".", recursive: bool = False) -> ToolResult:
        start_time = time.perf_counter()
        dir_path = self._resolve_path(path)

        if not dir_path.exists() or not dir_path.is_dir():
            return ToolResult(
                tool_name="list_dir",
                success=False,
                output="",
                error=f"Directory does not exist: {path}",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

        entries = []
        try:
            items = sorted(os.listdir(dir_path))
            for item in items:
                if item.startswith(".") and item != ".gitignore":
                    continue
                p = dir_path / item
                if p.is_dir():
                    entries.append(f"[DIR]  {item}/")
                else:
                    size_kb = round(p.stat().st_size / 1024, 1)
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
        else:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                output="",
                error=f"Unknown tool '{tool_name}'. Available tools: bash, read_file, write_file, edit_file, grep_search, glob_files, list_dir."
            )

tool_manager = ToolManager()
