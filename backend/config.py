import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "SYNORA AI"
    VERSION: str = "0.5.0"
    TAGLINE: str = "Many Minds. One Intelligence. Supercharged by OmniRoute."
    
    # OmniRoute High-Performance AI Router & Proxy Gateway Settings
    OMNIROUTE_BASE_URL: str = os.getenv("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1")
    OMNIROUTE_API_KEY: str = os.getenv("OMNIROUTE_API_KEY", "")
    OMNIROUTE_ENABLED: bool = os.getenv("OMNIROUTE_ENABLED", "true").lower() == "true"
    OMNIROUTE_TIMEOUT_SECONDS: float = float(os.getenv("OMNIROUTE_TIMEOUT_SECONDS", "300.0"))
    OMNIROUTE_FALLBACK_TO_OLLAMA: bool = os.getenv("OMNIROUTE_FALLBACK_TO_OLLAMA", "true").lower() == "true"

    # Routing & Provider Strategy ("auto", "omniroute", "ollama", "hybrid")
    DEFAULT_PROVIDER: str = os.getenv("SYNORA_DEFAULT_PROVIDER", "auto")
    DEFAULT_CLAW_MODEL: str = os.getenv("DEFAULT_CLAW_MODEL", "auto")

    # Ollama settings optimized for Apple Silicon M2 (16GB RAM)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_KEEP_ALIVE: int = int(os.getenv("OLLAMA_KEEP_ALIVE", "0"))  # 0 unloads immediately from VRAM
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300.0"))
    
    # M2 Memory Safeguards
    MAX_LOADED_MODELS: int = 1
    ENFORCE_SEQUENTIAL_ORCHESTRATION: bool = True
    
    # Development & Graceful Fallback Inference: Simulation enabled when offline
    ALLOW_SIMULATION: bool = os.getenv("SYNORA_ALLOW_SIMULATION", "true").lower() == "true"
    
    # Defaults
    DEFAULT_STARTER_TRIO: list[str] = [
        "qwen2.5-coder:7b",
        "deepseek-r1:7b",
        "llama3.1:8b"
    ]

settings = Settings()
