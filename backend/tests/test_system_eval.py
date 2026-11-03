import unittest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from backend.core.eval_system import run_system_evaluation, system_evaluator
from backend.core.router import router
from backend.models.registry import model_registry, ModelProfile
from backend.database.sqlite import (
    record_model_tool_call,
    get_model_tool_stats,
    record_routing_telemetry,
    update_routing_feedback,
    get_routing_accuracy_metrics,
    redact_sensitive_data
)
from backend.agent.tools import tool_manager
from backend.agent.approval import approval_manager

class TestSystemEvaluationAndHardening(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_repeatable_benchmark_all_categories_pass(self):
        """Verifies the 7-dimension benchmark runs and achieves 100% passing results."""
        report = run_system_evaluation()
        self.assertTrue(report["passed_all"], f"Benchmark failed: {report}")
        self.assertEqual(report["overall_score_pct"], 100.0)
        self.assertIn("routing_accuracy", report["categories"])
        self.assertIn("tool_selection", report["categories"])
        self.assertIn("permission_safety", report["categories"])
        self.assertIn("task_success", report["categories"])
        self.assertIn("claim_accuracy", report["categories"])
        self.assertIn("reliability", report["categories"])
        self.assertIn("sensitive_data_redaction", report["categories"])

    def test_model_selection_prefiltering_and_tool_rate(self):
        """Verifies pre-filtering unavailable models and empirical tool success scoring."""
        # Record some tool calls for qwen2.5-coder:7b
        record_model_tool_call("qwen2.5-coder:7b", True)
        record_model_tool_call("qwen2.5-coder:7b", True)
        stats = get_model_tool_stats("qwen2.5-coder:7b")
        self.assertGreater(stats["attempted"], 0)
        self.assertEqual(stats["success_rate"], 1.0)

        # In simulation mode, cloud flagships like claude-3-7-sonnet can be chosen
        best_sim, _, _ = router.select_best_model(
            target_role="specialist",
            domain="coding",
            complexity="medium",
            requires_tools=True,
            simulate=True,
            return_details=True
        )
        self.assertIsInstance(best_sim, str)

        # In real mode (simulate=False), uninstalled models are pre-filtered out before scoring
        # and fallback is reported
        best_real, fb_used, fb_reason = router.select_best_model(
            target_role="specialist",
            domain="coding",
            complexity="medium",
            requires_tools=True,
            simulate=False,
            return_details=True
        )
        self.assertIsInstance(best_real, str)
        self.assertTrue(fb_used)
        self.assertIsNotNone(fb_reason)

    def test_tool_argument_validation(self):
        """Verifies tool arguments are validated before execution."""
        # bash with empty command
        val, err = tool_manager.validate_tool_arguments("bash", {"command": ""})
        self.assertFalse(val)
        self.assertIn("Argument 'command' must be a non-empty string", err)

        # edit_file missing old_string
        val, err = tool_manager.validate_tool_arguments("edit_file", {"path": "a.py", "old_string": ""})
        self.assertFalse(val)
        self.assertIn("Argument 'old_string' must be a non-empty string", err)

        # valid edit_file
        val, err = tool_manager.validate_tool_arguments("edit_file", {"path": "a.py", "old_string": "x = 1", "new_string": "x = 2"})
        self.assertTrue(val)
        self.assertIsNone(err)

    def test_approval_diff_and_command_preview(self):
        """Verifies diff_preview and command_preview generation for pending actions."""
        # edit_file action
        aid = approval_manager.register_pending_action(
            session_id="test_diff_sess",
            tool_name="edit_file",
            arguments={"path": "main.py", "old_string": "def old():\n    pass\n", "new_string": "def new():\n    pass\n"},
            reason="Refactoring old to new",
            workspace_root="/workspace"
        )
        action = approval_manager._pending_actions.get(aid)
        self.assertIsNotNone(action)
        self.assertIsNotNone(action.diff_preview)
        self.assertIn("--- a/main.py", action.diff_preview)
        self.assertIn("+++ b/main.py", action.diff_preview)

        # bash action
        aid2 = approval_manager.register_pending_action(
            session_id="test_diff_sess",
            tool_name="bash",
            arguments={"command": "npm run test:coverage"},
            reason="Run tests",
            workspace_root="/workspace"
        )
        action2 = approval_manager._pending_actions.get(aid2)
        self.assertIsNotNone(action2)
        self.assertIsNotNone(action2.command_preview)
        self.assertIn("[/workspace] $ npm run test:coverage", action2.command_preview)

    def test_sensitive_data_redaction(self):
        """Verifies API keys, tokens, passwords, and private keys are scrubbed."""
        sample = (
            "export KEY=sk-1234567890abcdef123456\n"
            "GH_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234\n"
            "Authorization: Bearer secret_bearer_token_xyz_123456\n"
            "password: 'my_top_secret_db_pass'"
        )
        sanitized = redact_sensitive_data(sample)
        self.assertNotIn("sk-1234567890abcdef123456", sanitized)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz1234", sanitized)
        self.assertNotIn("secret_bearer_token_xyz_123456", sanitized)
        self.assertNotIn("my_top_secret_db_pass", sanitized)
        self.assertIn("[REDACTED_API_KEY]", sanitized)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", sanitized)

    def test_routing_feedback_and_metrics_endpoints(self):
        """Verifies API endpoints for feedback, metrics, and eval runs."""
        # 1. Feedback endpoint
        resp = self.client.post("/api/routing/feedback", json={
            "session_id": "test_sess_fb",
            "user_override": "chat",
            "is_correct": False
        })
        self.assertEqual(resp.status_code, 200)

        # 2. Metrics endpoint
        resp = self.client.get("/api/routing/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("routing", data)
        self.assertIn("models", data)

        # 3. Eval run endpoint
        resp = self.client.post("/api/eval/run")
        self.assertEqual(resp.status_code, 200)
        eval_data = resp.json()
        self.assertTrue(eval_data["passed_all"])
        self.assertEqual(eval_data["overall_score_pct"], 100.0)

if __name__ == "__main__":
    unittest.main()
