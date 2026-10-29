import os
import time
import json
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel

from backend.config import settings

class OmniRouteClient:
    """
    Client for OmniRoute High-Performance AI Router & Proxy Gateway.
    Enables SYNORA to leverage 376+ LLM providers, auto-fallbacks, circuit breakers,
    and intelligent multi-model combo routing via standard OpenAI-compatible endpoints.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ):
        self.base_url = (base_url or settings.OMNIROUTE_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.OMNIROUTE_API_KEY
        self.timeout = timeout or settings.OMNIROUTE_TIMEOUT_SECONDS

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SYNORA-AI-Agent/0.5.0 (OmniRoute-Integrated)"
        }
        key = self.api_key or settings.OMNIROUTE_API_KEY
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def check_health(self) -> Dict[str, Any]:
        """Checks if OmniRoute gateway is running and returns available models count."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    models_list = data.get("data", []) or data.get("models", [])
                    ids = [m.get("id") for m in models_list if isinstance(m, dict) and "id" in m]
                    return {
                        "status": "connected",
                        "online": True,
                        "base_url": self.base_url,
                        "models_count": len(ids),
                        "models": ids
                    }
                return {
                    "status": "error",
                    "online": False,
                    "status_code": res.status_code,
                    "message": f"OmniRoute returned HTTP {res.status_code}: {res.text[:150]}"
                }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "online": False,
                "message": f"Could not connect to OmniRoute at {self.base_url}. Ensure OmniRoute is running ('npm run dev')."
            }
        except Exception as e:
            return {
                "status": "error",
                "online": False,
                "message": str(e)
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """Fetches all models exposed by OmniRoute."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/models", headers=self._headers())
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", []) or data.get("models", [])
        except Exception:
            pass
        return []

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Executes a chat completion through OmniRoute's /v1/chat/completions."""
        start = time.perf_counter()
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if temperature is not None:
            payload["temperature"] = temperature

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers()
                )
                elapsed_ms = (time.perf_counter() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    msg = choices[0].get("message", {}) if choices else {}
                    content = msg.get("content", "") or ""
                    tool_calls = msg.get("tool_calls", []) or []
                    return {
                        "success": True,
                        "content": content,
                        "tool_calls": tool_calls,
                        "raw": data,
                        "elapsed_ms": elapsed_ms,
                        "provider": "omniroute",
                        "model": model
                    }
                else:
                    return {
                        "success": False,
                        "content": "",
                        "tool_calls": [],
                        "error": f"OmniRoute HTTP {resp.status_code}: {resp.text}",
                        "status_code": resp.status_code,
                        "elapsed_ms": elapsed_ms,
                        "provider": "omniroute"
                    }
        except httpx.ConnectError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "content": "",
                "tool_calls": [],
                "error": f"Connection refused to OmniRoute at {self.base_url}. Ensure OmniRoute is running ('npm run dev').",
                "is_connection_error": True,
                "elapsed_ms": elapsed_ms,
                "provider": "omniroute"
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "content": "",
                "tool_calls": [],
                "error": str(e),
                "elapsed_ms": elapsed_ms,
                "provider": "omniroute"
            }

omniroute_client = OmniRouteClient()
