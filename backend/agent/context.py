import os
from pathlib import Path
from typing import Dict, Any, List, Optional

class ProjectContextLoader:
    """
    Project memory and context extractor adapted from Claw Code's memory file resolver.
    Loads project guidelines (CLAUDE.md, CLAW.md, AGENTS.md, README.md) into the agent's context.
    """

    MEMORY_FILENAMES = ["CLAUDE.md", "CLAW.md", "AGENTS.md", "README.md"]

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()

    def set_workspace_root(self, path: str):
        self.workspace_root = Path(path).resolve()

    def get_workspace_root(self) -> str:
        return str(self.workspace_root)

    def discover_memory_files(self) -> List[Dict[str, Any]]:
        found = []
        for fname in self.MEMORY_FILENAMES:
            fpath = self.workspace_root / fname
            if fpath.exists() and fpath.is_file():
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    # Cap content to 4000 characters to prevent context overflow
                    preview = content[:4000]
                    found.append({
                        "file_name": fname,
                        "path": str(fpath),
                        "content": preview,
                        "char_count": len(content)
                    })
                except Exception:
                    continue
        return found

    def build_system_prompt_context(self) -> str:
        files = self.discover_memory_files()
        if not files:
            return ""

        sections = ["\n--- PROJECT KNOWLEDGE & GUIDELINES ---"]
        for f in files:
            sections.append(f"### File: {f['file_name']}\n{f['content']}\n")
        sections.append("--- END PROJECT GUIDELINES ---\n")
        return "\n".join(sections)

context_loader = ProjectContextLoader()
