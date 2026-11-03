import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.core.workflow_router import workflow_router, WorkflowType, WorkflowDecision
from backend.core.router import router
from backend.main import app

class TestWorkflowRouter(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_explain_this_code_routes_to_chat(self):
        queries = [
            "Explain this code",
            "Can you explain how async/await works in Python?",
            "What does this function do?",
            "Overview of TCP vs UDP protocols",
            "Teach me about Python decorators"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision: WorkflowDecision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CHAT)
                self.assertIsNone(decision.permission_mode)
                self.assertEqual(decision.suggested_runtime, "orchestrator")

    def test_find_bug_in_project_routes_to_claw_read_only(self):
        queries = [
            "Find the bug in my project",
            "Find bugs across the codebase",
            "Search where Router is defined in the repo",
            "Inspect the project files for memory leaks",
            "Audit my codebase for security issues"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision: WorkflowDecision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CLAW_READ_ONLY)
                self.assertEqual(decision.permission_mode, "read_only")
                self.assertEqual(decision.suggested_runtime, "claw_agent")

    def test_fix_bug_and_run_tests_routes_to_claw_confirmation(self):
        queries = [
            "Fix the bug and run tests",
            "Fix bugs in my project and run pytest",
            "Refactor auth in the project and run tests",
            "Implement missing method in backend/core/router.py and test it",
            "Fix the failing test and commit changes"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision: WorkflowDecision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CLAW_CONFIRMATION)
                self.assertEqual(decision.permission_mode, "ask")
                self.assertEqual(decision.suggested_runtime, "claw_agent")

    def test_ambiguous_requests_route_to_clarification(self):
        vague_queries = [
            "fix it",
            "fix the bug",
            "why is it failing",
            "make it work",
            "it doesn't work",
            "debug this",
            "run it"
        ]
        for q in vague_queries:
            with self.subTest(query=q):
                decision: WorkflowDecision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CLARIFICATION)
                self.assertIsNotNone(decision.clarification_question)
                self.assertIsNotNone(decision.clarification_options)
                self.assertEqual(decision.suggested_runtime, "clarification")

    def test_ambiguity_resolved_by_context(self):
        # A vague prompt with explicit context or code fence is not ambiguous
        decision = workflow_router.classify(
            prompt="fix it",
            context="Traceback: File backend/main.py, line 42 in <module> NameError: name 'foo' is not defined"
        )
        self.assertNotEqual(decision.workflow_type, WorkflowType.CLARIFICATION)

    def test_ambiguity_resolved_by_code_fence(self):
        decision = workflow_router.classify(
            prompt="fix it: ```python\ndef foo(): return 1/0\n```"
        )
        self.assertNotEqual(decision.workflow_type, WorkflowType.CLARIFICATION)

    def test_router_integration_async(self):
        async def run_async_tests():
            # 1. "Explain this code" -> Chat
            dec_chat = await router.route("Explain this code", simulate=True)
            self.assertEqual(dec_chat.workflow.workflow_type, WorkflowType.CHAT)
            self.assertFalse(dec_chat.is_agentic_task)

            # 2. "Find the bug in my project" -> Claw Read-Only
            dec_find = await router.route("Find the bug in my project", simulate=True)
            self.assertEqual(dec_find.workflow.workflow_type, WorkflowType.CLAW_READ_ONLY)
            self.assertEqual(dec_find.workflow.permission_mode, "read_only")
            self.assertTrue(dec_find.is_agentic_task)

            # 3. "Fix the bug and run tests" -> Claw Confirmation
            dec_fix = await router.route("Fix the bug and run tests", simulate=True)
            self.assertEqual(dec_fix.workflow.workflow_type, WorkflowType.CLAW_CONFIRMATION)
            self.assertEqual(dec_fix.workflow.permission_mode, "ask")
            self.assertTrue(dec_fix.is_agentic_task)

            # 4. "fix it" -> Clarification
            dec_clarify = await router.route("fix it", simulate=True)
            self.assertEqual(dec_clarify.task_type, "clarification")
            self.assertEqual(dec_clarify.workflow.workflow_type, WorkflowType.CLARIFICATION)

        asyncio.run(run_async_tests())

    def test_fix_login_bug_without_run_tests(self):
        queries = [
            "fix the login bug",
            "Fix the login bug in auth.py",
            "resolve the signup crash",
            "fix the payment error"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CLAW_CONFIRMATION)
                self.assertEqual(decision.permission_mode, "ask")

    def test_explain_and_fix_compound_request(self):
        queries = [
            "explain and fix this file",
            "explain the error and fix it",
            "review and fix the database schema"
        ]
        for q in queries:
            with self.subTest(query=q):
                decision = workflow_router.classify(q)
                self.assertEqual(decision.workflow_type, WorkflowType.CLAW_CONFIRMATION)
                self.assertEqual(decision.permission_mode, "ask")

    def test_hindi_hinglish_prompts(self):
        cases = [
            ("bhai login bug fix kar de", WorkflowType.CLAW_CONFIRMATION, "ask"),
            ("login chal nahi raha theek kardo", WorkflowType.CLAW_CONFIRMATION, "ask"),
            ("ye code explain karo", WorkflowType.CHAT, None),
            ("code me bug dhoondho", WorkflowType.CLAW_READ_ONLY, "read_only"),
            ("project me bug search karo", WorkflowType.CLAW_READ_ONLY, "read_only"),
        ]
        for prompt, expected_type, expected_perm in cases:
            with self.subTest(prompt=prompt):
                decision = workflow_router.classify(prompt)
                self.assertEqual(decision.workflow_type, expected_type)
                self.assertEqual(decision.permission_mode, expected_perm)

    def test_context_aware_followup_resolves_ambiguity(self):
        context = "User: The auth endpoint in backend/auth.py is raising AttributeError: NoneType object has no attribute 'token'"
        decision = workflow_router.classify("fix it", context=context)
        self.assertEqual(decision.workflow_type, WorkflowType.CLAW_CONFIRMATION)
        self.assertEqual(decision.permission_mode, "ask")

    def test_api_chat_clarification_response(self):
        response = self.client.post("/api/chat", json={"prompt": "fix it", "simulate": True})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["task_type"], "clarification")
        self.assertEqual(data["execution_mode"], "workflow_clarification")
        self.assertIn("ambiguous", data["final_response"].lower())

if __name__ == "__main__":
    unittest.main()
