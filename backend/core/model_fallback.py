# SYNORA v0.5.0 - Multi-Model Availability & Fallback Preferences (OmniRoute + Ollama)

FALLBACK_MODELS = {
    "general": [
        "omniroute-auto",
        "claude-3-7-sonnet",
        "gpt-4o",
        "gemini-2.0-flash",
        "llama-3.3-70b",
        "llama3.1:8b",
        "llama3.2:3b",
        "llama3.2:1b",
        "qwen2.5:7b",
        "gemma3:4b",
        "qwen2.5-coder:7b"
    ],

    "coding": [
        "claude-3-7-sonnet",
        "claude-3-5-sonnet",
        "deepseek-chat",
        "qwen-2.5-coder-32b",
        "qwen2.5-coder:7b",
        "deepseek-coder:6.7b",
        "qwen3:4b",
        "llama3.1:8b",
        "llama3.2:1b"
    ],

    "reasoning": [
        "deepseek-reasoner",
        "claude-3-7-sonnet",
        "deepseek-r1:7b",
        "qwen3:8b",
        "phi4-mini",
        "qwen3:4b",
        "llama3.1:8b",
        "llama3.2:1b"
    ],

    "synthesis": [
        "gpt-4o",
        "gemini-2.0-flash",
        "llama-3.3-70b",
        "claude-3-7-sonnet",
        "llama3.1:8b",
        "llama3.2:3b",
        "llama3.2:1b",
        "qwen3:4b",
        "gemma3:4b",
        "qwen2.5-coder:7b"
    ]
}
