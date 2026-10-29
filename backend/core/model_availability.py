import httpx
from typing import Set, List, Optional
from backend.config import settings

OLLAMA_URL = settings.OLLAMA_BASE_URL
OMNIROUTE_URL = settings.OMNIROUTE_BASE_URL

class NoModelsAvailableError(Exception):
    """Raised when real inference is requested but no AI models are reachable via OmniRoute or Ollama."""
    def __init__(self, message: Optional[str] = None, suggested_install: Optional[List[str]] = None):
        self.message = message or (
            "SYNORA cannot perform real inference: no models available.\n"
            "Ensure either OmniRoute is running ('npm run dev') or Ollama is running ('ollama serve')."
        )
        self.suggested_install = suggested_install or [
            "npm run dev  # (Starts OmniRoute proxy for 376 providers)",
            "ollama serve && ollama pull qwen2.5-coder:7b"
        ]
        super().__init__(self.message)


class OllamaOfflineError(Exception):
    """Raised when both Ollama and OmniRoute are offline."""
    def __init__(self, message: Optional[str] = None):
        self.message = message or (
            f"Could not connect to OmniRoute ({OMNIROUTE_URL}) or Ollama ({OLLAMA_URL}).\n"
            "Start OmniRoute ('npm run dev') or Ollama ('ollama serve')."
        )
        self.suggested_install = [
            "npm run dev",
            "ollama serve"
        ]
        super().__init__(self.message)


class ModelAvailability:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_URL
        self.installed_models: Set[str] = set()
        self.ollama_models: Set[str] = set()
        self.omniroute_models: Set[str] = set()
        self.is_online: bool = False
        self.is_ollama_online: bool = False
        self.is_omniroute_online: bool = False
        self.last_error: Optional[str] = None
        self._mock_mode: bool = False
        self._last_refresh_time: float = 0.0

    async def refresh(self, force: bool = False) -> Set[str]:
        """Fetch installed/available models from both OmniRoute and Ollama with a 5s TTL cache."""
        if self._mock_mode:
            return self.installed_models

        import time
        now = time.time()
        if not force and (now - self._last_refresh_time < 5.0) and self.installed_models:
            return self.installed_models

        self._last_refresh_time = now
        self.installed_models = set()
        self.ollama_models = set()
        self.omniroute_models = set()
        self.is_ollama_online = False
        self.is_omniroute_online = False

        from backend.models.registry import model_registry

        # 1. Probe OmniRoute Gateway (OpenAI-compatible proxy for 376 providers)
        if settings.OMNIROUTE_ENABLED:
            try:
                from backend.core.omniroute_client import omniroute_client
                health = await omniroute_client.check_health()
                if health.get("online"):
                    self.is_omniroute_online = True
                    fetched_ids = health.get("models", [])
                    # Include flagship defaults and any fetched IDs
                    tier0_ids = [m.id for m in model_registry.list_models() if getattr(m, "provider", None) == "omniroute"]
                    all_omni = set(fetched_ids + tier0_ids)
                    self.omniroute_models = all_omni
                    self.installed_models.update(all_omni)
                    model_registry.sync_with_omniroute(list(all_omni))
            except Exception as exc:
                self.is_omniroute_online = False

        # 2. Probe Ollama Daemon
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    ollama_names = {model["name"] for model in data.get("models", [])}
                    self.ollama_models = ollama_names
                    self.installed_models.update(ollama_names)
                    self.is_ollama_online = True
                    model_registry.sync_with_ollama(list(ollama_names))
        except Exception:
            self.is_ollama_online = False

        self.is_online = self.is_omniroute_online or self.is_ollama_online

        if not self.is_online:
            self.last_error = (
                f"Neither OmniRoute ({OMNIROUTE_URL}) nor Ollama ({self.base_url}) is reachable. "
                f"Please start OmniRoute ('npm run dev') or Ollama ('ollama serve')."
            )
        else:
            self.last_error = None

        return self.installed_models

    def is_omniroute_model(self, model_name: str) -> bool:
        if not model_name:
            return False
        clean = model_name.strip().lower()
        if clean in {m.lower() for m in self.omniroute_models}:
            return True
        from backend.models.registry import model_registry
        profile = model_registry.get(model_name)
        if profile and getattr(profile, "provider", None) == "omniroute":
            return True
        # Common cloud model prefixes
        cloud_prefixes = ["claude", "gpt", "o1", "o3", "deepseek", "gemini", "omniroute"]
        return any(clean.startswith(p) for p in cloud_prefixes)

    def is_installed(self, model_name: str) -> bool:
        if not model_name:
            return False

        # Direct exact match
        if model_name in self.installed_models:
            return True

        if self.is_omniroute_online and self.is_omniroute_model(model_name):
            return True

        # Normalized / prefix comparison (e.g. tag variants)
        clean_target = model_name.strip().lower()
        target_base = clean_target.split(":")[0]

        for installed in self.installed_models:
            clean_inst = installed.strip().lower()
            if clean_target == clean_inst:
                return True
            inst_base = clean_inst.split(":")[0]
            if target_base == inst_base:
                if ":" in clean_target:
                    target_tag = clean_target.split(":")[1]
                    if target_tag in clean_inst:
                        return True
                else:
                    return True

        return False

    def select_available(self, candidates: List[str], exclude: Optional[Set[str]] = None) -> Optional[str]:
        excluded = exclude or set()
        for model in candidates:
            if model not in excluded and self.is_installed(model):
                return model

        # If OmniRoute is online and no specific candidate matched, pick the first omniroute model
        if self.is_omniroute_online and self.omniroute_models:
            for m in self.omniroute_models:
                if m not in excluded:
                    return m

        return None

model_availability = ModelAvailability()
