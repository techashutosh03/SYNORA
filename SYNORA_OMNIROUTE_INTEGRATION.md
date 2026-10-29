# 🚀 SYNORA AI + CLAW CODE + OMNIROUTE INTEGRATION

> **Many Minds. One Intelligence. Supercharged by 376 LLM Providers.**

This repository unifies **SYNORA AI** and **Claw Code** with **OmniRoute**, transforming SYNORA from a local-only open-weight orchestrator into an enterprise-grade, multi-model autonomous software engineering powerhouse connected to **376 cloud & local AI providers** with automated failover, auto-combo routing, and resilient circuit breaking.

---

## ⚡ Unified Architecture Overview

```text
                                  SYNORA AI
                        Many Minds. One Intelligence.
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
       SYNORA CHAT (Web UI)                           CLAW CODE HARNESS
   (Multi-Model Orchestration)                      (CLI & Claw Studio)
              │                                               │
              ├───────────────────────────────────────────────┤
              ▼                                               ▼
     SYNORA Intelligent Router                   Autonomous Agent Loop
 (Domain / Role / Complexity Analysis)          (Multi-Turn Tool Execution)
              │                                               │
              └───────────────────────┬───────────────────────┘
                                      ▼
                        SYNORA UNIVERSAL GATEWAY
                  (backend/core/omniroute_client.py)
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
      OMNIROUTE SUPER-ENGINE                         LOCAL OLLAMA DAEMON
   (http://127.0.0.1:20128/v1)                   (http://127.0.0.1:11434)
              │                                               │
  ┌───────────┼───────────┐                       ┌───────────┼───────────┐
  ▼           ▼           ▼                       ▼           ▼           ▼
Claude 3.7  GPT-4o   DeepSeek R1               Qwen 2.5    DeepSeek R1   Llama 3.1
 (Sonnet)   (OpenAI)  (Reasoner)                (Coder 7B)    (7B)         (8B)
  ▲           ▲           ▲                       ▲           ▲           ▲
  └───────────┴───────────┴───────────────────────┴───────────┴───────────┘
                                      │
                      3-Mechanism Resilience Engine
           (Circuit Breakers · Connection Cooldown · Model Lockout)
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
   Unified Synthesized Code                       Verified Working Workspace
```

---

## 🔌 Core Integration Components

| Component | Location | Description |
|---|---|---|
| **OmniRoute Client** | `backend/core/omniroute_client.py` | Asynchronous OpenAI-compatible client providing access to OmniRoute's 376 providers, streaming SSE, and tool dispatch. |
| **Hybrid Model Availability** | `backend/core/model_availability.py` | Dynamically probes OmniRoute (`/v1/models`) and Ollama (`/api/tags`), seamlessly unifying cloud and local models. |
| **OmniRoute Model Registry** | `backend/models/registry.py` | Auto-registers cloud flagships (Claude 3.7 Sonnet, GPT-4o, DeepSeek R1/V3, Gemini 2.0 Flash) and dynamically imports custom providers. |
| **Multi-Model Orchestrator** | `backend/core/orchestrator.py` | Dispatches multi-stage pipelines (`_call_model`) across heterogeneous providers with automatic fallback between OmniRoute and Ollama. |
| **Claw Code Agent Loop** | `backend/agent/loop.py` | Multi-turn autonomous coding loop with native OpenAI function calling over OmniRoute and Ollama. |
| **Claw Code CLI** | `./claw` / `backend/agent/cli.py` | Terminal REPL with `--model` and `--provider` selection, `/doctor` diagnostics, and real-time status. |
| **Unified Launcher** | `./synora` | Single entry point to start OmniRoute + SYNORA Backend + SYNORA Frontend simultaneously or individually. |

---

## 🛠️ Quickstart & Usage Guide

### 1. Launch All Services (OmniRoute + SYNORA Backend + Web UI)

Run the unified launcher from repository root:

```bash
./synora
# OR
./synora dev
# OR
npm run synora:all
```

This concurrently boots:
- **OmniRoute AI Gateway** on `http://localhost:20128`
- **SYNORA FastAPI Backend** on `http://localhost:8000`
- **SYNORA Web UI (Chat & Claw Studio)** on `http://localhost:5173`

---

### 2. Launching Individual Components

```bash
# Start ONLY OmniRoute Gateway (port 20128)
./synora omniroute

# Start ONLY SYNORA FastAPI Backend (port 8000)
./synora backend

# Start ONLY SYNORA Frontend Web UI (port 5173)
./synora frontend

# Run Preflight System & Provider Diagnostics
./synora doctor
```

---

### 3. Using Claw Code Terminal CLI (`./claw`)

Launch the autonomous agent anywhere in your workspace:

```bash
# Interactive REPL (auto-detects OmniRoute or Ollama)
./claw

# Run with a specific flagship model via OmniRoute
./claw --model claude-3-7-sonnet "Refactor backend/core/router.py to optimize cache lookup"
./claw --model gpt-4o "Implement unit tests for omniroute_client"
./claw --model deepseek-reasoner "Audit security permissions and tool boundaries"

# Run single-shot diagnostic and status commands
./claw /doctor
./claw /status
./claw /diff
./claw /model
```

---

## ⚙️ Configuration & Environment

Settings can be customized via `.env` or environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OMNIROUTE_BASE_URL` | `http://127.0.0.1:20128/v1` | URL for OmniRoute OpenAI-compatible gateway |
| `OMNIROUTE_API_KEY` | `""` | Optional API key / bearer token for OmniRoute authentication |
| `OMNIROUTE_ENABLED` | `true` | Enable or disable OmniRoute gateway bridge |
| `OMNIROUTE_FALLBACK_TO_OLLAMA` | `true` | Automatically fallback to local Ollama if an upstream cloud provider fails |
| `SYNORA_DEFAULT_PROVIDER` | `auto` | Preferred provider: `auto`, `omniroute`, or `ollama` |
| `DEFAULT_CLAW_MODEL` | `auto` | Default model for Claw Code (resolves to top coding model) |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama daemon URL |
| `SYNORA_ALLOW_SIMULATION` | `false` | Enable transparent simulation mode for dev/testing without active models |

---

## 🧪 Testing

Run the full unified backend test suite (including OmniRoute integration tests):

```bash
python3 -m unittest discover -s backend/tests
```

