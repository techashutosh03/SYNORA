# SYNORA AI 🚀 + CLAW CODE 🦞
> **Many Minds. One Intelligence. Autonomous Coding Agent Harness.**

SYNORA AI is a unified multi-model platform that orchestrates open-weight artificial intelligence models into a single, cohesive intelligence. Fully integrated with **Claw Code**, SYNORA provides an autonomous software engineering harness capable of multi-turn code generation, surgical refactoring, git automation, and terminal execution.

---

## ⚡ Unified Architecture Overview

```text
                  SYNORA AI + CLAW CODE
              Many Minds. One Intelligence.
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
  SYNORA CHAT (Web UI)                  CLAW CODE HARNESS
(Multi-Model Orchestration)            (CLI & Studio Engine)
        │                                       │
  Intelligent Router                   Autonomous Agent Loop
        │                                       │
  ┌─────┼─────┐                         ┌───────┼───────┐
  ▼     ▼     ▼                         ▼       ▼       ▼
DeepSeek Qwen Llama                  Filesystem Shell  Git Engine
(Reason)(Code)(Synthesize)           (read/edit)(bash) (diff/commit)
        │                                       │
  Unified Output                        Verified Working Code
```

---

## 🦞 Claw Code Integration Features

| Capability | CLI (`./claw`) | Web UI (Claw Studio) |
|---|---|---|
| **Interactive REPL** | `./claw` | Live Event Stream (`http://localhost:5173`) |
| **Preflight Doctor** | `./claw doctor` | One-click `🩺 /doctor` button |
| **Git Status & Branch** | `./claw status` | Top workspace badge with dirty file count |
| **Working Diff** | `./claw diff` | Syntax-highlighted Diff tab |
| **Code Review** | `./claw review` | Autonomous multi-model review of git diff |
| **Smart Commits** | `./claw commit` | One-click semantic commit generator |
| **Project Guidance** | Auto-loads `CLAUDE.md`/`AGENTS.md` | "Project Guidelines" viewer |
| **Security Gates** | `autonomous`, `ask`, `read_only` | Interactive approval banner |
| **Native Tools (12+)** | `bash`, `read`, `write`, `edit`, `grep`, `glob`, `list_dir`, `git_status`, `git_diff`, `git_commit`, `web_fetch`, `todo_write` | Live cards with duration metrics |

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| **Project Name** | SYNORA AI + Claw Code |
| **Model Catalog** | 30 open-weight models (Qwen 2.5 Coder, DeepSeek R1, Llama 3.1, etc.) |
| **Agent Engine** | Claw Code Autonomous Multi-Turn Loop with Native Tool Calling |
| **Claw Code Canonical Core** | Rust Cargo Workspace (`claw-code/rust`) + Python parity suite |
| **Inference Engine** | Local Ollama (M2 memory-safe: sequential execution with `keep_alive=0`) |
| **Backend API** | Python 3.10+ & FastAPI |
| **Frontend UI** | React 19 + Vite + Tailwind CSS (Dual-mode: Chat + Claw Studio) |
| **Database** | SQLite (`synora.db`) |
| **Target Device** | Apple Silicon M2, 16GB RAM |

---

## 📁 Project Structure

```text
SYNORA/
│
├── claw                      # Executable CLI launcher for Claw Code agent
├── synora                    # Unified launcher (starts dev server or CLI)
│
├── claw-code/                # Canonical Claw Code Repository
│   ├── rust/                 # 11-crate Cargo workspace (claw binary, runtime, tools, commands)
│   ├── src/                  # Python parity & porting workspace
│   ├── docs/                 # Gate verification maps & documentation
│   ├── tests/                # Claw Code test suite
│   ├── USAGE.md              # Claw Code usage manual
│   └── ROADMAP.md            # Active roadmap & backlog
│
├── backend/
│   ├── main.py               # FastAPI application with REST & SSE endpoints
│   ├── config.py             # Settings & M2 memory optimization limits
│   │
│   ├── agent/                # SYNORA Claw Code Harness
│   │   ├── cli.py            # Terminal REPL & CLI parser
│   │   ├── loop.py           # Multi-turn autonomous agent loop
│   │   ├── tools.py          # 12+ native tools (bash, edit_file, git, etc.)
│   │   ├── commands.py       # Slash command engine (/doctor, /diff, /review, etc.)
│   │   ├── permissions.py    # Security gate & destructive command filters
│   │   └── context.py        # Project memory resolver (CLAUDE.md / AGENTS.md)
│   │
│   ├── core/                 # SYNORA Multi-Model Engine (Router, Orchestrator, Synthesizer)
│   ├── models/               # 30-model catalog & Ollama bridge
│   └── database/             # SQLite session & telemetry storage
│
├── frontend/                 # React UI
│   ├── src/
│   │   ├── components/
│   │   │   ├── ClawStudio.jsx         # Claw Code Studio Agent Workspace
│   │   │   ├── Header.jsx             # Dual-mode switcher (Chat vs Claw Studio)
│   │   │   ├── ChatArea.jsx           # Multi-model collaborative chat
│   │   │   └── ModelActivityDrawer.jsx# Real-time orchestration visualizer
│   │   └── services/api.js            # Unified REST + SSE API client
│   └── package.json
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Set Up Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Pull Recommended Models (Ollama)

```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-r1:7b
ollama pull llama3.1:8b
```

*(Note: If Ollama is offline or models are still downloading, SYNORA and Claw Code operate in transparent simulation / dev mode so you can test all tools, diagnostics, and endpoints immediately).*

---

## 💻 Using Claw Code via Terminal CLI

Launch Claw Code anywhere in your project using the `./claw` script:

### Interactive REPL
```bash
./claw
```
Inside the REPL:
- Type any task: `Refactor backend/core/router.py to improve cache lookup`
- Run slash commands:
  - `/doctor` — Preflight system & workspace diagnostics
  - `/status` — Show git branch, uncommitted files, and project memory
  - `/diff` — View git diff of modifications
  - `/review` — Run autonomous code review
  - `/commit` — Stage and commit with structured semantic message
  - `/tools` — List all registered native tools
  - `/permissions` — Toggle mode (`autonomous`, `ask`, `read_only`)
  - `/help` — View command manual
  - `/exit` — Quit REPL

### Single-Shot Commands
```bash
./claw doctor                             # Run diagnostic check
./claw status                             # Check workspace status
./claw diff                               # View git diff
./claw "Fix syntax error in router.py"    # Autonomous single task execution
```

---

## 🌐 Using Claw Code via Web UI (Claw Code Studio)

1. **Start the Backend**:
   ```bash
   uvicorn backend.main:app --reload --port 8000
   ```
2. **Start the Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```
3. Open **`http://localhost:5173`**
4. In the top navigation bar, toggle from **SYNORA Chat** to **Claw Code Studio**.
5. Pick your target workspace directory, run tasks, inspect real-time tool calls and diffs, and execute slash commands with one click!

---

## 🔌 Unified API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/claw/doctor` | `GET` | Preflight diagnostic health check report |
| `/api/claw/status` | `GET` | Workspace path, git branch, modified files, memory files |
| `/api/claw/diff` | `GET` | Git diff of uncommitted modifications |
| `/api/claw/slash` | `POST` | Execute slash commands (`/doctor`, `/review`, `/diff`, `/commit`, `/init`) |
| `/api/claw/workspace` | `POST` | Change or validate active workspace directory |
| `/api/agent/stream` | `POST` | Real-time SSE streaming of agent reasoning, tool execution, and diffs |
| `/api/agent/task` | `POST` | Run autonomous coding task end-to-end |
| `/api/agent/tools` | `GET` | Catalog of 12+ native execution tools |
| `/api/agent/permissions` | `GET/POST` | Inspect or update security gate mode (`autonomous`, `ask`, `read_only`) |
| `/api/chat/stream` | `POST` | SSE streaming for multi-model collaborative chat |
| `/api/health` | `GET` | Ollama connection, RAM metrics, and M2 settings |

---

## 🧪 Testing

Run the full unified test suite:

```bash
python3 -m unittest discover -s backend/tests
```

All 13 unit tests validate:
- Tool execution lifecycle (`read_file`, `write_file`, `edit_file`, `grep_search`, `glob_files`, `git_status`, `git_diff`, `todo_write`)
- Security gate enforcement against destructive commands
- Slash command registry (`/doctor`, `/status`, `/diff`, `/init`, `/help`, `/permissions`)
- Autonomous multi-turn agent loop dispatch

---

## 📜 Canonical Rust Workspace

The original Claw Code Rust implementation lives in `claw-code/rust`:
```bash
cd claw-code/rust
cargo build --workspace
./target/debug/claw doctor
```

---

## 🎯 SYNORA Version Roadmap

- [x] **v0.1**: Model Registry (30 models), Router, Orchestrator, Synthesizer, Evaluator, FastAPI backend.
- [x] **v0.2**: Real Ollama server configuration, sequential M2 memory safeguards, unified collaborative synthesis.
- [x] **v0.3**: Multi-turn conversation memory, intelligent multi-factor model selection, real-time performance monitoring.
- [x] **v0.4**: Complete React + Vite + Tailwind CSS interface with live multi-model orchestration visualizer, streaming responses, conversation history, and model management.
- [x] **v0.5**: **Claw Code Autonomous Agent Harness Integration**:
  - Full canonical Claw Code repository integrated in `claw-code/`
  - Interactive CLI REPL (`./claw`) with colored output and slash commands
  - Dedicated **Claw Code Studio** Web UI with real-time SSE streaming, collapsible tool execution cards, and diff inspection
  - 12+ Native tools (`bash`, `read_file`, `write_file`, `edit_file`, `grep_search`, `glob_files`, `list_dir`, `git_status`, `git_diff`, `git_commit`, `web_fetch`, `todo_write`)
  - Complete slash command engine (`/doctor`, `/review`, `/diff`, `/commit`, `/status`, `/init`, `/compact`, `/cost`, `/tools`, `/permissions`, `/model`, `/help`)
  - Security gates with granular path protection and destructive command filtering
- [ ] **v0.6**: ChromaDB vector store, semantic RAG search & document embeddings.
- [ ] **v1.0**: Automated multi-stage testing, code execution sandbox, production deployment.
