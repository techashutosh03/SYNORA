# SYNORA AI 🚀
> **Many Minds. One Intelligence.**

SYNORA AI is a unified multi-model AI system that orchestrates the capabilities of open-weight artificial intelligence models into a single, cohesive intelligence.

---

## ⚡ Architecture Overview

```text
                  SYNORA AI
           Many Minds. One Intelligence.
                       │
                 User Question
                       │
                  SYNORA CORE
                       │
              Intelligent Router
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       DeepSeek       Qwen         Llama
       Phi-4          Mistral      Gemma
       StarCoder      Granite      Others (30 Cataloged)
          │            │            │
          └────────────┼────────────┘
                       │
               SYNORA SYNTHESIS
                       │
                 ONE RESPONSE
                       │
                     USER
```

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Project Name** | SYNORA AI |
| **Model Catalog** | 30 open-weight models (Qwen, DeepSeek, Llama, Mistral, Phi, etc.) |
| **Inference Engine** | Ollama |
| **Backend** | Python 3.10+ & FastAPI |
| **Orchestration** | Custom Sequential Multi-Model Pipeline (M2 Memory-Safe) |
| **Database** | SQLite (`synora.db`) |
| **Vector Database** | ChromaDB *(Milestone v0.3)* |
| **Target Device** | MacBook Air M2, 16GB RAM |

---

## 📁 Project Structure

```text
SYNORA/
│
├── backend/
│   ├── main.py               # FastAPI application & REST endpoints
│   ├── config.py             # Settings & M2 memory optimization limits
│   ├── requirements.txt      # Python dependencies
│   │
│   ├── core/
│   │   ├── router.py         # Sub-millisecond intent & complexity router
│   │   ├── orchestrator.py   # Sequential pipeline execution (keep_alive=0)
│   │   ├── synthesizer.py    # Output merging & attribution formatting
│   │   └── evaluator.py      # Multi-model consensus & conflict evaluation
│   │
│   ├── models/
│   │   └── registry.py       # 30-model catalog, roles, and Ollama sync
│   │
│   └── database/
│       └── sqlite.py         # Chat & orchestration trace persistence
│
├── frontend/                 # React UI (Milestone v0.4)
├── config/                   # Global configuration files
└── README.md
```

---

## 💻 Apple Silicon M2 (16GB RAM) Optimizations

To run smoothly on a 16GB MacBook Air without memory pressure or excessive swapping:
1. **Ollama Server Flags**:
   ```bash
   export OLLAMA_MAX_LOADED_MODELS=1
   export OLLAMA_NUM_PARALLEL=1
   ollama serve
   ```
2. **Immediate VRAM Release (`keep_alive=0`)**:
   SYNORA automatically passes `"keep_alive": 0` on every inference call, guaranteeing that models are unloaded immediately upon completing their stage.
3. **Sequential Execution**:
   Models are invoked in series (e.g. Qwen generates code $\rightarrow$ DeepSeek audits logic $\rightarrow$ Llama synthesizes), ensuring only 1 model resides in memory at any point in time.

---

## 🚀 Quickstart Guide

### 1. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Pull Milestone 0.1 Starter Models (in Ollama)

```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:7b
ollama pull llama3.1:8b
```

*(Note: If Ollama is not installed or models are not yet pulled, SYNORA operates in a transparent simulation fallback mode so you can test all API endpoints and orchestration pipelines immediately).*

### 3. Start the SYNORA Backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Interactive API documentation will be available at:
👉 **`http://localhost:8000/docs`**

### 4. Start the SYNORA Frontend (v0.4)

```bash
cd frontend
npm install
npm run dev
```

The SYNORA AI user interface will be live at:
👉 **`http://localhost:5173`**

---

## 🔌 API Endpoints (v0.4)

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | `GET` | System health, Ollama status, storage check, and M2 optimization settings |
| `/api/settings` | `GET/POST` | Inspect and configure runtime flags (e.g. Simulation Mode, M2 limits) |
| `/api/metrics` | `GET` | Real-time telemetry, model latency averages, RAM consumption, and disk metrics |
| `/api/models` | `GET` | List all 30 models with roles, specialties, and installed status |
| `/api/models/select` | `POST` | Update active models in the routing pool |
| `/api/chat` | `POST` | Multi-turn contextual chat with multi-factor routing and unified synthesis |
| `/api/chat/stream` | `POST` | Server-Sent Events (SSE) streaming with live stage transitions & token output |
| `/api/conversations` | `GET` | List all active conversation sessions and turn summaries |
| `/api/conversations/{session_id}` | `GET` | Retrieve full chronological message history for a session |
| `/api/history` | `GET` | Retrieve previous chat conversations and orchestration traces |
| `/api/agent/task` | `POST` | Execute autonomous coding tasks using Claw Code tools (`bash`, `edit_file`, `grep`, etc.) |
| `/api/agent/stream` | `POST` | Real-time SSE streaming of agent thoughts, tool execution, and diffs |
| `/api/agent/tools` | `GET` | Retrieve the active catalog of native Claw Code tools |
| `/api/agent/execute` | `POST` | Directly dispatch a single tool with security gate validation |
| `/api/agent/permissions`| `GET/POST`| Inspect and configure permission mode (`autonomous`, `ask`, `read_only`) |

---

## 🎯 SYNORA Version Roadmap

- [x] **v0.1**: Model Registry (30 models), Router, Orchestrator, Synthesizer, Evaluator, FastAPI backend.
- [x] **v0.2**: Real Ollama server configuration, sequential M2 memory safeguards, unified collaborative synthesis.
- [x] **v0.3**: Multi-turn conversation memory, intelligent multi-factor model selection, real-time performance monitoring.
- [x] **v0.4**: Complete React + Vite + Tailwind CSS interface with live multi-model orchestration visualizer, streaming responses, conversation history, and model management.
- [x] **v0.5**: **Claw Code Agent Engine Integration**: Native tool execution (`bash`, `edit_file`, `read_file`, `grep_search`, `glob_files`, `list_dir`), permission security gates, project memory context (`CLAUDE.md`/`AGENTS.md`), and real-time SSE agent streaming.
- [ ] **v0.6**: ChromaDB vector store, semantic RAG search & document embeddings.
- [ ] **v1.0**: Automated multi-stage testing, code execution sandbox, production deployment.


