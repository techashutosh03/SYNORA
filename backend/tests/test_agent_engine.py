import unittest
import asyncio
import tempfile
import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.agent.tools import ToolManager
from backend.agent.permissions import PermissionEnforcer
from backend.agent.context import ProjectContextLoader
from backend.agent.loop import AgentLoop

class TestAgentEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="synora_agent_test_")
        self.tool_mgr = ToolManager(workspace_root=self.test_dir)
        self.enforcer = PermissionEnforcer(workspace_root=self.test_dir)
        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_tool_definitions(self):
        tools = self.tool_mgr.get_tool_definitions()
        names = [t["function"]["name"] for t in tools]
        expected = ["bash", "read_file", "write_file", "edit_file", "grep_search", "glob_files", "list_dir"]
        for exp in expected:
            self.assertIn(exp, names)

    def test_file_operations_roundtrip(self):
        # 1. Write file
        w_res = asyncio.run(self.tool_mgr.execute_write_file("test.txt", "line 1\nline 2\nline 3\n"))
        self.assertTrue(w_res.success)
        self.assertTrue((Path(self.test_dir) / "test.txt").exists())

        # 2. Read file
        r_res = asyncio.run(self.tool_mgr.execute_read_file("test.txt"))
        self.assertTrue(r_res.success)
        self.assertIn("line 2", r_res.output)

        # 3. Edit file (surgical replace)
        e_res = asyncio.run(self.tool_mgr.execute_edit_file("test.txt", "line 2", "line TWO"))
        self.assertTrue(e_res.success)

        # 4. Verify edit
        r_res2 = asyncio.run(self.tool_mgr.execute_read_file("test.txt"))
        self.assertIn("line TWO", r_res2.output)
        self.assertNotIn("line 2", r_res2.output)

    def test_grep_and_glob(self):
        asyncio.run(self.tool_mgr.execute_write_file("src/main.py", "def compute_magic():\n    return 42\n"))
        asyncio.run(self.tool_mgr.execute_write_file("src/utils.py", "# Helper utils\n"))

        # Grep search
        grep_res = asyncio.run(self.tool_mgr.execute_grep_search("compute_magic", path="."))
        self.assertTrue(grep_res.success)
        self.assertIn("compute_magic", grep_res.output)

        # Glob search
        glob_res = asyncio.run(self.tool_mgr.execute_glob_files("src/*.py"))
        self.assertTrue(glob_res.success)
        self.assertIn("src/main.py", glob_res.output)
        self.assertIn("src/utils.py", glob_res.output)

    def test_bash_execution(self):
        bash_res = asyncio.run(self.tool_mgr.execute_bash("echo 'SYNORA_ONLINE'"))
        self.assertTrue(bash_res.success)
        self.assertIn("SYNORA_ONLINE", bash_res.output)

    def test_permission_enforcer(self):
        # 1. Dangerous command blocking
        dec = self.enforcer.check_tool_permission("bash", {"command": "rm -rf /"})
        self.assertFalse(dec.allowed)

        # 2. Safe command allowed
        dec2 = self.enforcer.check_tool_permission("bash", {"command": "git status"})
        self.assertTrue(dec2.allowed)

        # 3. Read only mode
        self.enforcer.set_mode("read_only")
        dec3 = self.enforcer.check_tool_permission("write_file", {"path": "a.txt", "content": "test"})
        self.assertFalse(dec3.allowed)

    def test_context_loader(self):
        loader = ProjectContextLoader(workspace_root=self.test_dir)
        (Path(self.test_dir) / "AGENTS.md").write_text("# Test Agent Specs\nUse pytest.", encoding="utf-8")
        ctx = loader.build_system_prompt_context()
        self.assertIn("Use pytest", ctx)

    def test_api_endpoints(self):
        # Tools catalog endpoint
        res = self.client.get("/api/agent/tools")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["tools_count"], 7)

        # Permissions endpoint
        res_p = self.client.get("/api/agent/permissions")
        self.assertEqual(res_p.status_code, 200)
        self.assertIn("mode", res_p.json())

if __name__ == "__main__":
    unittest.main()
