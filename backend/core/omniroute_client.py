import os
import time
import json
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel

from backend.config import settings

import os
import time
import json
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel

from backend.config import settings

# Battle-tested cloud models exposed through OmniRoute with zero API key configuration needed
VERIFIED_FREE_MODELS: List[str] = [
    "ddgw/claude-haiku-4-5",     # Anthropic Claude 4.5 Haiku
    "ddgw/gpt-5.4-mini",         # OpenAI GPT
    "ddgw/mistral-small-2603",   # Mistral Small
    "ddgw/tinfoil/gpt-oss-120b", # Open-source 120B reasoning model
    "ddgw/tinfoil/gemma4-31b",   # Google Gemma 4 31B
]

# Canonical mapping from SYNORA generic/role identifiers to exact OmniRoute models
MODEL_ALIAS_MAP: Dict[str, str] = {
    # Auto & general combos
    "omniroute-auto": "ddgw/claude-haiku-4-5",
    "omniroute": "ddgw/claude-haiku-4-5",
    "auto": "ddgw/claude-haiku-4-5",
    "auto/chat": "ddgw/claude-haiku-4-5",
    "auto/best-chat": "ddgw/claude-haiku-4-5",
    "auto/best-fast": "ddgw/gpt-5.4-mini",
    "auto/fast": "ddgw/gpt-5.4-mini",
    "auto/coding": "ddgw/gpt-5.4-mini",
    "auto/best-coding": "ddgw/gpt-5.4-mini",
    "auto/reasoning": "ddgw/claude-haiku-4-5",
    "auto/best-reasoning": "ddgw/claude-haiku-4-5",
    "auto/best-free": "ddgw/claude-haiku-4-5",

    # Flagship aliases
    "omniroute-claude": "ddgw/claude-haiku-4-5",
    "omniroute-claude-3.5-sonnet": "ddgw/claude-haiku-4-5",
    "omniroute-gpt": "ddgw/gpt-5.4-mini",
    "omniroute-gpt-4o": "ddgw/gpt-5.4-mini",
    "omniroute-mistral": "ddgw/mistral-small-2603",
    "omniroute-gemma": "ddgw/tinfoil/gemma4-31b",
    "omniroute-deepseek-v3": "ddgw/tinfoil/gpt-oss-120b",
    "omniroute-llama-3.3-70b": "ddgw/tinfoil/gpt-oss-120b",

    # Local Ollama model redirects when routing through OmniRoute
    "qwen2.5-coder:7b": "ddgw/gpt-5.4-mini",
    "qwen2.5-coder:1.5b": "ddgw/gpt-5.4-mini",
    "deepseek-r1:7b": "ddgw/claude-haiku-4-5",
    "deepseek-r1:1.5b": "ddgw/claude-haiku-4-5",
    "llama3.2:3b": "ddgw/claude-haiku-4-5",
    "llama3.2:1b": "ddgw/claude-haiku-4-5",
    "mistral:7b": "ddgw/mistral-small-2603",
    "gemma2:2b": "ddgw/tinfoil/gemma4-31b",
    "phi3.5:3.8b": "ddgw/gpt-5.4-mini",
}

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

    def resolve_model(self, model: str) -> str:
        """Resolves alias or generic model ID to concrete OmniRoute model."""
        if not model:
            return VERIFIED_FREE_MODELS[0]
        return MODEL_ALIAS_MAP.get(model, model)

    async def check_health(self) -> Dict[str, Any]:
        """Checks if OmniRoute gateway is running and returns available models count."""
        try:
            async with httpx.AsyncClient(timeout=3.5) as client:
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
                "message": f"{type(e).__name__}: {str(e)}"
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

    async def _post_chat(
        self,
        client: httpx.AsyncClient,
        target_model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> httpx.Response:
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "stream": stream
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if temperature is not None:
            payload["temperature"] = temperature

        return await client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers()
        )

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Executes a chat completion through OmniRoute's /v1/chat/completions.
        Automatically resolves model aliases and handles transparent fallback across
        OmniRoute's flagship provider pool so requests never fail unexpectedly.
        """
        start = time.perf_counter()
        target_model = self.resolve_model(model)

        # Candidates to try in sequence: target model first, then verified free fallbacks
        candidates: List[str] = [target_model]
        for fb in VERIFIED_FREE_MODELS:
            if fb not in candidates:
                candidates.append(fb)

        last_error: Optional[str] = None
        last_status_code: Optional[int] = None

        for idx, candidate in enumerate(candidates):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await self._post_chat(
                        client=client,
                        target_model=candidate,
                        messages=messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        temperature=temperature,
                        stream=stream
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
                            "model": candidate,
                            "requested_model": model
                        }
                    else:
                        last_status_code = resp.status_code
                        last_error = f"OmniRoute HTTP {resp.status_code}: {resp.text}"
                        # If unknown model (400) or upstream provider issue (502/503), try next fallback candidate
                        if resp.status_code in (400, 404, 500, 502, 503) and idx < len(candidates) - 1:
                            continue
            except httpx.ConnectError:
                # Connection refused - OmniRoute might be down or booting
                elapsed_ms = (time.perf_counter() - start) * 1000
                # Try auto-booting OmniRoute if managed
                try:
                    from backend.core.omniroute_process import omniroute_process_manager
                    if await omniroute_process_manager.ensure_online_async(wait_seconds=6.0):
                        # Retry once with target_model
                        async with httpx.AsyncClient(timeout=self.timeout) as retry_client:
                            retry_resp = await self._post_chat(
                                client=retry_client,
                                target_model=target_model,
                                messages=messages,
                                tools=tools,
                                tool_choice=tool_choice,
                                temperature=temperature,
                                stream=stream
                            )
                            if retry_resp.status_code == 200:
                                data = retry_resp.json()
                                choices = data.get("choices", [])
                                msg = choices[0].get("message", {}) if choices else {}
                                return {
                                    "success": True,
                                    "content": msg.get("content", "") or "",
                                    "tool_calls": msg.get("tool_calls", []) or [],
                                    "raw": data,
                                    "elapsed_ms": (time.perf_counter() - start) * 1000,
                                    "provider": "omniroute",
                                    "model": target_model,
                                    "requested_model": model
                                }
                except Exception:
                    pass

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
                last_error = f"{type(e).__name__}: {str(e)}"
                if idx < len(candidates) - 1:
                    continue

        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "success": False,
            "content": "",
            "tool_calls": [],
            "error": last_error or "Unknown OmniRoute error",
            "status_code": last_status_code,
            "elapsed_ms": elapsed_ms,
            "provider": "omniroute",
            "model": target_model
        }

omniroute_client = OmniRouteClient()
