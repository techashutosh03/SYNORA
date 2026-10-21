import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "SYNORA AI"
    VERSION: str = "0.4.4"
    TAGLINE: str = "Many Minds. One Intelligence."
    
    # Ollama settings optimized for Apple Silicon M2 (16GB RAM)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_KEEP_ALIVE: int = int(os.getenv("OLLAMA_KEEP_ALIVE", "0"))  # 0 unloads immediately from VRAM
    OLLAMA_TIMEOUT_SECONDS: float = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300.0"))
    
    # M2 Memory Safeguards
    MAX_LOADED_MODELS: int = 1
    ENFORCE_SEQUENTIAL_ORCHESTRATION: bool = True
    
    # Production Inference: Simulation strictly disabled by default
    ALLOW_SIMULATION: bool = os.getenv("SYNORA_ALLOW_SIMULATION", "false").lower() == "true"
    
    # Defaults
    DEFAULT_STARTER_TRIO: list[str] = [
        "qwen2.5-coder:7b",
        "deepseek-r1:7b",
        "llama3.1:8b"
    ]

settings = Settings()
