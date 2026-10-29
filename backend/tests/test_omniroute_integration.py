import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.models.registry import model_registry
from backend.core.model_availability import model_availability
from backend.core.omniroute_client import omniroute_client
from backend.core.orchestrator import orchestrator
from backend.agent.loop import agent_loop

client = TestClient(app)

class TestOmniRouteIntegration(unittest.TestCase):

    def setUp(self):
        settings.OMNIROUTE_ENABLED = True
        settings.ALLOW_SIMULATION = True

    def test_omniroute_client_headers(self):
        settings.OMNIROUTE_API_KEY = "test-key-123"
        headers = omniroute_client._headers()
        self.assertEqual(headers["Authorization"], "Bearer test-key-123")
        self.assertIn("SYNORA-AI-Agent", headers["User-Agent"])

    @patch("backend.core.omniroute_client.httpx.AsyncClient")
    def test_sync_with_omniroute_dynamic_models(self, mock_client_cls):
        discovered_models = ["claude-3-7-sonnet", "gpt-4o", "my-custom-fine-tune"]
        model_registry.sync_with_omniroute(discovered_models)

        # Check claude-3-7-sonnet exists and is marked installed & omniroute
        claude = model_registry.get("claude-3-7-sonnet")
        self.assertIsNotNone(claude)
        self.assertTrue(claude.is_installed)
        self.assertEqual(claude.provider, "omniroute")
        self.assertEqual(claude.specialty, "coding")

        # Check custom fine-tune dynamically registered
        custom = model_registry.get("my-custom-fine-tune")
        self.assertIsNotNone(custom)
        self.assertTrue(custom.is_installed)
        self.assertEqual(custom.provider, "omniroute")

    @patch("backend.core.omniroute_client.omniroute_client.check_health")
    def test_model_availability_omniroute_online(self, mock_health):
        mock_health.return_value = {
            "status": "connected",
            "online": True,
            "base_url": "http://127.0.0.1:20128/v1",
            "models_count": 3,
            "models": ["claude-3-7-sonnet", "gpt-4o", "deepseek-reasoner"]
        }

        import asyncio
        asyncio.run(model_availability.refresh())

        self.assertTrue(model_availability.is_omniroute_online)
        self.assertTrue(model_availability.is_online)
        self.assertTrue(model_availability.is_installed("claude-3-7-sonnet"))
        self.assertTrue(model_availability.is_omniroute_model("claude-3-7-sonnet"))

    def test_omniroute_endpoints(self):
        with patch.object(omniroute_client, "check_health", new_callable=AsyncMock) as mock_chk:
            mock_chk.return_value = {
                "status": "connected",
                "online": True,
                "base_url": "http://127.0.0.1:20128/v1",
                "models_count": 2,
                "models": ["claude-3-7-sonnet", "gpt-4o"]
            }
            res = client.get("/api/omniroute/status")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("online"))
            self.assertEqual(data.get("models_count"), 2)

    def test_health_includes_omniroute(self):
        with patch.object(omniroute_client, "check_health", new_callable=AsyncMock) as mock_chk:
            mock_chk.return_value = {
                "status": "connected",
                "online": True,
                "base_url": "http://127.0.0.1:20128/v1",
                "models_count": 5,
                "models": ["claude-3-7-sonnet", "gpt-4o"]
            }
            res = client.get("/api/health")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertIn("omniroute", data)
            self.assertEqual(data["omniroute"]["online"], True)

    @patch("backend.core.omniroute_client.omniroute_client.chat_completion")
    def test_orchestrator_routes_to_omniroute(self, mock_chat):
        mock_chat.return_value = {
            "success": True,
            "content": "Synthesized code from OmniRoute gateway.",
            "tool_calls": [],
            "elapsed_ms": 150.0,
            "provider": "omniroute"
        }

        import asyncio
        res = asyncio.run(orchestrator._call_omniroute("claude-3-7-sonnet", [{"role": "user", "content": "hi"}]))
        self.assertTrue(res["success"])
        self.assertEqual(res["provider"], "omniroute")
        self.assertIn("OmniRoute gateway", res["content"])

if __name__ == "__main__":
    unittest.main()

