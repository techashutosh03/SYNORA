import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path

from backend.agent.tools import tool_manager, ToolResult
from backend.agent.permissions import permission_enforcer
from backend.agent.commands import slash_command_registry
from backend.agent.loop import agent_loop
from backend.agent.context import context_loader

class TestClawIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        tool_manager.set_workspace_root(str(self.test_dir))
        slash_command_registry.set_workspace_root(str(self.test_dir))
        context_loader.set_workspace_root(str(self.test_dir))
        permission_enforcer.set_mode("autonomous")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_file_write_read_edit_lifecycle(self):
        async def run_test():
            # 1. Write file
            w_res = await tool_manager.execute_write_file("sample.py", "def hello():\n    print('Hello World')\n")
            self.assertTrue(w_res.success)
            self.assertTrue((self.test_dir / "sample.py").exists())

            # 2. Read file
            r_res = await tool_manager.execute_read_file("sample.py", start_line=1, end_line=2)
            self.assertTrue(r_res.success)
            self.assertIn("Hello World", r_res.output)

            # 3. Edit file
            e_res = await tool_manager.execute_edit_file(
                "sample.py",
                old_string="print('Hello World')",
                new_string="print('Hello Claw Code & SYNORA')"
            )
            self.assertTrue(e_res.success)
            content = (self.test_dir / "sample.py").read_text()
            self.assertIn("Hello Claw Code & SYNORA", content)

        asyncio.run(run_test())

    def test_search_and_glob(self):
        async def run_test():
            await tool_manager.execute_write_file("src/app.py", "class AppRouter:\n    pass\n")
            await tool_manager.execute_write_file("src/utils.py", "# Utility helper\n")

            # Glob
            g_res = await tool_manager.execute_glob_files("src/*.py")
            self.assertTrue(g_res.success)
            self.assertIn("src/app.py", g_res.output)
            self.assertIn("src/utils.py", g_res.output)

            # Grep
            grep_res = await tool_manager.execute_grep_search("AppRouter", path="src")
            self.assertTrue(grep_res.success)
            self.assertIn("AppRouter", grep_res.output)

        asyncio.run(run_test())

    def test_todo_write(self):
        async def run_test():
            todos = [
                {"id": "1", "task": "Design agent harness", "status": "completed"},
                {"id": "2", "task": "Verify doctor diagnostics", "status": "in_progress"}
            ]
            t_res = await tool_manager.execute_todo_write(todos)
            self.assertTrue(t_res.success)
            self.assertTrue((self.test_dir / ".claw" / "todos.json").exists())

        asyncio.run(run_test())

    def test_security_gate_blocks_destructive_commands(self):
        # Destructive bash patterns must be rejected
        fork_bomb = ":(){ :|:& };:"
        dec1 = permission_enforcer.check_tool_permission("bash", {"command": fork_bomb})
        self.assertFalse(dec1.allowed)

        rm_rf = "rm -rf /"
        dec2 = permission_enforcer.check_tool_permission("bash", {"command": rm_rf})
        self.assertFalse(dec2.allowed)

        # In read_only mode, write tools must be rejected
        permission_enforcer.set_mode("read_only")
        dec3 = permission_enforcer.check_tool_permission("write_file", {"path": "test.txt", "content": "hi"})
        self.assertFalse(dec3.allowed)

        # In read_only mode, read tools are allowed
        dec4 = permission_enforcer.check_tool_permission("read_file", {"path": "test.txt"})
        self.assertTrue(dec4.allowed)

    def test_slash_commands(self):
        async def run_test():
            # /help
            res_help = await slash_command_registry.execute("/help")
            self.assertTrue(res_help.success)
            self.assertIn("/doctor", res_help.output)
            self.assertIn("/status", res_help.output)

            # /tools
            res_tools = await slash_command_registry.execute("/tools")
            self.assertTrue(res_tools.success)
            self.assertIn("bash", res_tools.output)
            self.assertIn("read_file", res_tools.output)

            # /permissions
            res_perm = await slash_command_registry.execute("/permissions ask")
            self.assertTrue(res_perm.success)
            self.assertEqual(permission_enforcer.mode, "ask")

            # /init
            res_init = await slash_command_registry.execute("/init")
            self.assertTrue(res_init.success)
            self.assertTrue((self.test_dir / "CLAUDE.md").exists())
            self.assertTrue((self.test_dir / ".claw.json").exists())

            # /doctor
            res_doc = await slash_command_registry.execute("/doctor")
            self.assertTrue(res_doc.success)
            self.assertIn("CLAW CODE PREFLIGHT DOCTOR REPORT", res_doc.output)

        asyncio.run(run_test())

    def test_agent_loop_slash_command_dispatch(self):
        async def run_test():
            res = await agent_loop.run(task="/help", workspace_root=str(self.test_dir))
            self.assertTrue(res.success)
            self.assertIn("CLAW CODE SLASH COMMANDS", res.final_response)
            self.assertEqual(res.tools_used, ["/help"])

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
