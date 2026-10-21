import httpx
from typing import Set, List, Optional
from backend.config import settings

OLLAMA_URL = settings.OLLAMA_BASE_URL


class NoModelsAvailableError(Exception):
    """Raised when real inference is requested but no compatible AI models are installed in Ollama."""
    def __init__(self, message: Optional[str] = None, suggested_install: Optional[List[str]] = None):
        self.message = message or "SYNORA cannot perform real inference because no compatible AI models are installed."
        self.suggested_install = suggested_install or [
            "ollama pull llama3.2:3b",
            "ollama pull qwen2.5-coder:7b"
        ]
        super().__init__(self.message)


class OllamaOfflineError(Exception):
    """Raised when Ollama daemon is not running or unreachable."""
    def __init__(self, message: Optional[str] = None):
        self.message = message or f"Could not connect to Ollama at {OLLAMA_URL}. Ensure Ollama is running ('ollama serve')."
        self.suggested_install = [
            "ollama serve",
            "ollama pull llama3.2:3b"
        ]
        super().__init__(self.message)


class ModelAvailability:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or OLLAMA_URL
        self.installed_models: Set[str] = set()
        self.is_online: bool = False
        self.last_error: Optional[str] = None
        self._mock_mode: bool = False

    async def refresh(self) -> Set[str]:
        """Fetch installed models from Ollama."""
        if self._mock_mode:
            return self.installed_models
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                self.installed_models = {
                    model["name"]
                    for model in data.get("models", [])
                }
                self.is_online = True
                self.last_error = None
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            self.installed_models = set()
            self.is_online = False
            self.last_error = f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve')."
        except Exception as exc:
            self.installed_models = set()
            self.is_online = False
            self.last_error = str(exc)

        return self.installed_models

    def is_installed(self, model_name: str) -> bool:
        if not model_name:
            return False

        # Direct exact match
        if model_name in self.installed_models:
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
                # If target has tag (e.g., 7b or 8b), check if it matches installed
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

        return None


model_availability = ModelAvailability()
