# SYNORA v0.4.2 - Intelligent Model Availability & Fallback Preferences

FALLBACK_MODELS = {
    "general": [
        "llama3.1:8b",
        "llama3.2:3b",
        "llama3.2:1b",
        "qwen2.5:7b",
        "gemma3:4b",
        "qwen2.5-coder:7b"
    ],

    "coding": [
        "qwen2.5-coder:7b",
        "deepseek-coder:6.7b",
        "qwen3:4b",
        "llama3.1:8b",
        "llama3.2:1b"
    ],

    "reasoning": [
        "deepseek-r1:7b",
        "qwen3:8b",
        "phi4-mini",
        "qwen3:4b",
        "llama3.1:8b",
        "llama3.2:1b"
    ],

    "synthesis": [
        "llama3.1:8b",
        "llama3.2:3b",
        "llama3.2:1b",
        "qwen3:4b",
        "gemma3:4b",
        "qwen2.5-coder:7b"
    ]
}
