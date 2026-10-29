import time
import uuid
import json
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.models.registry import model_registry, ModelProfile
from backend.core.router import router, RoutingDecision
from backend.core.model_availability import model_availability, NoModelsAvailableError, OllamaOfflineError
from backend.core.orchestrator import Orchestrator, OrchestrationResult, OllamaInferenceError, ModelUnavailableError
from backend.core.synthesizer import synthesizer, SynthesisInsight, SynthesisResult
from backend.core.evaluator import evaluator, EvaluationMetric
from backend.core.memory import memory
from backend.core.monitor import monitor
from backend.database.sqlite import save_chat_record, get_recent_history, get_session_history, get_all_sessions
from backend.agent import tool_manager, permission_enforcer, agent_loop, slash_command_registry, context_loader

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SYNORA AI: Many Minds. One Intelligence. Unified multi-model AI system."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = Orchestrator()

# --- Validation Helper ---

def validate_inference_mode(simulate: bool):
    """
    Validates that real inference is required when simulate is False.
    Never silently switch to simulation.
    """
    if simulate:
        return
    # Real inference is required.
    # Never silently switch to simulation.
    return

# --- Request / Response Schemas ---

class ChatRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, description="User query or instruction")
    message: Optional[str] = Field(default=None, description="Alternative alias for prompt")
    session_id: Optional[str] = Field(default=None, description="Conversation session ID for multi-turn memory")
    custom_models: Optional[List[str]] = Field(default=None, description="Optional manual override of models to use")
    simulate: bool = Field(default=False, description="Inference mode: True for simulation, False for real inference")

    def get_query(self) -> str:
        q = self.prompt or self.message
        if not q or not q.strip():
            raise HTTPException(status_code=422, detail="Either 'prompt' or 'message' must be provided.")
        return q.strip()

class ChatResponse(BaseModel):
    session_id: str
    user_prompt: str
    final_response: str
    task_type: str
    sub_domain: str
    complexity: str
    is_follow_up: bool
    models_used: List[str]
    total_time_ms: float
    routing_time_ms: float
    memory_rss_mb: float
    evaluation: EvaluationMetric
    synthesis_insights: Optional[SynthesisInsight] = None
    orchestration_stages: List[Dict[str, Any]]
    saved_id: Optional[int] = None
    execution_mode: str = "real"  # "real" or "simulated"
    simulated: bool = False
    is_simulated: bool = False

class SelectModelsRequest(BaseModel):
    model_ids: List[str] = Field(..., description="List of model IDs to set as active in the registry")

class SettingsUpdateRequest(BaseModel):
    allow_simulation: Optional[bool] = None
    max_loaded_models: Optional[int] = None
    keep_alive: Optional[int] = None

class AgentTaskRequest(BaseModel):
    task: str = Field(..., description="Coding or execution task description")
    model_id: Optional[str] = Field(default="qwen2.5-coder:7b", description="Model ID to execute agent loop")
    max_turns: int = Field(default=12, ge=1, le=30)
    workspace_root: Optional[str] = None

class SlashCommandRequest(BaseModel):
    command: str = Field(..., description="Slash command, e.g. /doctor, /status, /diff, /help")
    workspace_root: Optional[str] = None

class WorkspacePathRequest(BaseModel):
    path: str = Field(..., description="Directory path to set as active workspace")

class DirectToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class PermissionModeRequest(BaseModel):
    mode: str = Field(..., description="'autonomous', 'ask', or 'read_only'")


# --- API Endpoints ---

@app.get("/")
def read_root():
    return {
        "project": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/api/settings")
def get_settings():
    """Returns current system configuration and M2 memory parameters."""
    return {
        "allow_simulation": settings.ALLOW_SIMULATION,
        "max_loaded_models": settings.MAX_LOADED_MODELS,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "project_name": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": settings.VERSION
    }

@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest):
    """Updates runtime settings like simulation mode or M2 safeguards."""
    if req.allow_simulation is not None:
        settings.ALLOW_SIMULATION = req.allow_simulation
    if req.max_loaded_models is not None:
        settings.MAX_LOADED_MODELS = req.max_loaded_models
    if req.keep_alive is not None:
        settings.OLLAMA_KEEP_ALIVE = req.keep_alive
    return {
        "status": "updated",
        "settings": {
            "allow_simulation": settings.ALLOW_SIMULATION,
            "max_loaded_models": settings.MAX_LOADED_MODELS,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE
        }
    }

@app.get("/api/health")
async def check_health():
    """
    Checks system health, Ollama connectivity, storage health, and M2 optimization state.
    """
    ollama_status = await orchestrator.check_ollama_health()
    storage = monitor.get_storage_status()
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "ollama": ollama_status,
        "storage": storage,
        "allow_simulation": settings.ALLOW_SIMULATION,
        "m2_optimization": {
            "max_loaded_models": settings.MAX_LOADED_MODELS,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "sequential_orchestration": settings.ENFORCE_SEQUENTIAL_ORCHESTRATION,
            "recommended_env": "export OLLAMA_MAX_LOADED_MODELS=1 && export OLLAMA_NUM_PARALLEL=1"
        }
    }

@app.get("/api/models")
async def list_models(
    specialty: Optional[str] = None,
    role: Optional[str] = None,
    installed_only: bool = False,
    active_only: bool = False
):
    """
    Returns the catalog of 30 supported open-weight models with metadata.
    """
    await orchestrator.check_ollama_health()
    models = model_registry.list_models(
        specialty=specialty,
        role=role,
        installed_only=installed_only,
        active_only=active_only
    )
    return {
        "total_catalog_size": len(model_registry._models),
        "count": len(models),
        "models": models
    }

@app.post("/api/models/select")
def select_models(req: SelectModelsRequest):
    """
    Configures which models are active in the SYNORA routing pool.
    """
    model_registry.set_active_models(req.model_ids)
    active_models = model_registry.list_models(active_only=True)
    return {
        "message": f"Updated active models. {len(active_models)} models now active.",
        "active_models": [m.id for m in active_models]
    }

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    SYNORA Unified Chat:
    1. Multi-turn memory: retrieves conversation context for session_id.
    2. Intelligent Router: multi-factor fitness scoring & greeting detection.
    3. Orchestrator: sequential multi-model execution with M2 memory guardrails.
    4. Synthesis Engine: unified final answer with progression insights.
    5. Evaluator: model consensus and security conflict check.
    6. Performance Monitor: latency, RSS memory, and per-model statistics.
    7. Persistence: saves conversation turn to SQLite history.
    """
    start_total = time.perf_counter()
    user_query = request.get_query()
    session_id = request.session_id or str(uuid.uuid4())
    
    validate_inference_mode(request.simulate)
    is_simulated = bool(request.simulate)

    # Step 1: Conversation Context Retrieval
    context = memory.get_conversation_context(session_id)

    # Step 2: Multi-Factor Intelligent Routing
    try:
        routing: RoutingDecision = await router.route(user_query, context=context, simulate=is_simulated)
    except NoModelsAvailableError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "No Models Available",
                "message": e.message,
                "suggested_install": e.suggested_install,
                "execution_mode": "real",
                "simulated": False
            }
        )
    except OllamaOfflineError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Ollama Offline",
                "message": e.message,
                "suggested_install": e.suggested_install,
                "execution_mode": "real",
                "simulated": False
            }
        )
    plan = routing.plan

    # If custom models specified by user, override stages only if installed or simulating
    if request.custom_models:
        from backend.core.orchestrator import StageConfig
        if is_simulated:
            plan.stages = [
                StageConfig(stage_name=f"Custom Stage {i+1}", model_id=mid, role="specialist")
                for i, mid in enumerate(request.custom_models)
            ]
        else:
            installed_custom = [mid for mid in request.custom_models if model_availability.is_installed(mid)]
            if installed_custom:
                plan.stages = [
                    StageConfig(stage_name=f"Custom Stage {i+1}", model_id=mid, role="specialist")
                    for i, mid in enumerate(installed_custom)
                ]

    # Step 3: Multi-Model Orchestration
    try:
        orch_result: OrchestrationResult = await orchestrator.execute_plan(
            user_prompt=user_query,
            plan=plan,
            simulate=is_simulated
        )
    except ModelUnavailableError as e:
        monitor.record_request(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            task_type=routing.task_type,
            complexity=routing.complexity,
            total_time_ms=(time.perf_counter() - start_total) * 1000,
            routing_time_ms=routing.routing_time_ms,
            models_used=routing.recommended_models,
            stage_results=[],
            status="error"
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Model Unavailable",
                "message": f"The required AI model is not installed.\n\nModel: {e.model_id}\n\nInstall using:\nollama pull {e.model_id}",
                "model": e.model_id,
                "install_command": f"ollama pull {e.model_id}"
            }
        )
    except OllamaInferenceError as e:
        monitor.record_request(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            task_type=routing.task_type,
            complexity=routing.complexity,
            total_time_ms=(time.perf_counter() - start_total) * 1000,
            routing_time_ms=routing.routing_time_ms,
            models_used=routing.recommended_models,
            stage_results=[],
            status="error"
        )
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Inference Failed",
                "message": str(e)
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SYNORA Orchestration Error: {str(e)}")

    # Step 4: Synthesis
    synthesis_res: SynthesisResult = synthesizer.synthesize(
        prompt=user_query,
        stage_results=orch_result.stage_results
    )

    # Step 5: Quality & Consensus Evaluation
    eval_result = evaluator.evaluate(orch_result.stage_results, simulated=is_simulated)

    total_time_ms = round((time.perf_counter() - start_total) * 1000, 2)

    # Prepare trace
    stages_data = [
        {
            "stage_name": s.stage_name,
            "model_id": s.model_id,
            "role": s.role,
            "execution_time_ms": s.execution_time_ms,
            "status": s.status,
            "error_message": s.error_message,
            "preview": s.response[:300] + ("..." if len(s.response) > 300 else "")
        }
        for s in orch_result.stage_results
    ]

    # Step 6: Telemetry & Performance Monitoring
    req_metrics = monitor.record_request(
        request_id=str(uuid.uuid4()),
        session_id=session_id,
        task_type=routing.task_type,
        complexity=routing.complexity,
        total_time_ms=total_time_ms,
        routing_time_ms=routing.routing_time_ms,
        models_used=orch_result.models_used,
        stage_results=orch_result.stage_results,
        consistency_score=eval_result.consistency_score,
        status="success"
    )

    # Step 7: Persistence in SQLite
    record_id = save_chat_record(
        user_prompt=user_query,
        final_response=synthesis_res.final_response,
        task_type=routing.task_type,
        complexity=routing.complexity,
        models_used=orch_result.models_used,
        total_time_ms=total_time_ms,
        orchestration_trace={"stages": stages_data, "evaluation": eval_result.model_dump()},
        session_id=session_id,
        memory_rss_mb=req_metrics.memory_rss_mb
    )

    return ChatResponse(
        session_id=session_id,
        user_prompt=user_query,
        final_response=synthesis_res.final_response,
        task_type=routing.task_type,
        sub_domain=routing.sub_domain,
        complexity=routing.complexity,
        is_follow_up=routing.is_follow_up,
        models_used=orch_result.models_used,
        total_time_ms=total_time_ms,
        routing_time_ms=routing.routing_time_ms,
        memory_rss_mb=req_metrics.memory_rss_mb,
        evaluation=eval_result,
        synthesis_insights=synthesis_res.insights,
        orchestration_stages=stages_data,
        saved_id=record_id,
        execution_mode="simulated" if is_simulated else "real",
        simulated=is_simulated,
        is_simulated=is_simulated
    )

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming endpoint emitting Server-Sent Events (SSE):
    - routing: plan and model allocation
    - stage_start: model active in M2 pipeline
    - stage_complete: intermediate audit or proposal ready
    - synthesis_start: consolidated metrics and consensus
    - token: stream chunks of final response
    - done: final ChatResponse payload
    """
    user_query = request.get_query()
    session_id = request.session_id or str(uuid.uuid4())
    
    validate_inference_mode(request.simulate)
    is_simulated = bool(request.simulate)

    async def event_generator():
        start_total = time.perf_counter()
        
        # 1. Context retrieval
        context = memory.get_conversation_context(session_id)
        
        # 2. Routing
        try:
            routing: RoutingDecision = await router.route(user_query, context=context, simulate=is_simulated)
        except NoModelsAvailableError as e:
            err_payload = {
                "error": "No Models Available",
                "message": e.message,
                "suggested_install": e.suggested_install,
                "execution_mode": "real",
                "simulated": False
            }
            yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"
            return
        except OllamaOfflineError as e:
            err_payload = {
                "error": "Ollama Offline",
                "message": e.message,
                "suggested_install": e.suggested_install,
                "execution_mode": "real",
                "simulated": False
            }
            yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"
            return
        plan = routing.plan
        
        if request.custom_models:
            from backend.core.orchestrator import StageConfig
            if is_simulated:
                plan.stages = [
                    StageConfig(stage_name=f"Custom Stage {i+1}", model_id=mid, role="specialist")
                    for i, mid in enumerate(request.custom_models)
                ]
            else:
                installed_custom = [mid for mid in request.custom_models if model_availability.is_installed(mid)]
                if installed_custom:
                    plan.stages = [
                        StageConfig(stage_name=f"Custom Stage {i+1}", model_id=mid, role="specialist")
                        for i, mid in enumerate(installed_custom)
                    ]

        # Emit routing event
        routing_data = {
            "session_id": session_id,
            "task_type": routing.task_type,
            "sub_domain": routing.sub_domain,
            "complexity": routing.complexity,
            "is_follow_up": routing.is_follow_up,
            "execution_mode": "simulated" if is_simulated else "real",
            "simulated": is_simulated,
            "stages": [
                {"stage_name": s.stage_name, "model_id": s.model_id, "role": s.role}
                for s in plan.stages
            ]
        }
        yield f"event: routing\ndata: {json.dumps(routing_data)}\n\n"

        # 3. Multi-Model Pipeline Execution
        stage_results = []
        models_used = []
        
        for idx, stage in enumerate(plan.stages):
            yield f"event: stage_start\ndata: {json.dumps({'stage_index': idx, 'stage_name': stage.stage_name, 'model_id': stage.model_id, 'role': stage.role})}\n\n"
            
            single_plan = plan.model_copy()
            single_plan.stages = [stage]
            
            try:
                single_res = await orchestrator.execute_plan(
                    user_prompt=user_query,
                    plan=single_plan,
                    simulate=is_simulated
                )
                stage_res = single_res.stage_results[0]
            except ModelUnavailableError as e:
                err_payload = {
                    "error": "Model Unavailable",
                    "message": f"The required AI model is not installed.\n\nModel: {e.model_id}\n\nInstall using:\nollama pull {e.model_id}",
                    "model": e.model_id,
                    "install_command": f"ollama pull {e.model_id}",
                    "execution_mode": "real",
                    "simulated": False
                }
                yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"
                return
            except (OllamaInferenceError, Exception) as e:
                err_payload = {
                    "error": "Inference Failed",
                    "message": str(e),
                    "execution_mode": "real",
                    "simulated": False
                }
                yield f"event: error\ndata: {json.dumps(err_payload)}\n\n"
                return

            stage_results.append(stage_res)
            models_used.append(stage_res.model_id)

            yield f"event: stage_complete\ndata: {json.dumps({'stage_index': idx, 'stage_name': stage.stage_name, 'model_id': stage.model_id, 'role': stage.role, 'execution_time_ms': stage_res.execution_time_ms, 'status': stage_res.status, 'preview': stage_res.response[:250] + ('...' if len(stage_res.response) > 250 else '')})}\n\n"
            await asyncio.sleep(0.05)

        # 4. Synthesis
        synthesis_res = synthesizer.synthesize(prompt=user_query, stage_results=stage_results)
        eval_result = evaluator.evaluate(stage_results, simulated=is_simulated)

        yield f"event: synthesis_start\ndata: {json.dumps({'insights': synthesis_res.insights.model_dump(), 'evaluation': eval_result.model_dump()})}\n\n"

        # Stream synthesis response tokens smoothly
        full_text = synthesis_res.final_response
        words = full_text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
            yield f"event: token\ndata: {json.dumps({'delta': chunk})}\n\n"
            await asyncio.sleep(0.02)

        # 5. Telemetry & SQLite Save
        total_time_ms = round((time.perf_counter() - start_total) * 1000, 2)
        stages_data = [
            {
                "stage_name": s.stage_name,
                "model_id": s.model_id,
                "role": s.role,
                "execution_time_ms": s.execution_time_ms,
                "status": s.status,
                "error_message": s.error_message,
                "preview": s.response[:300] + ("..." if len(s.response) > 300 else "")
            }
            for s in stage_results
        ]
        req_metrics = monitor.record_request(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            task_type=routing.task_type,
            complexity=routing.complexity,
            total_time_ms=total_time_ms,
            routing_time_ms=routing.routing_time_ms,
            models_used=models_used,
            stage_results=stage_results,
            consistency_score=eval_result.consistency_score,
            status="success"
        )
        record_id = save_chat_record(
            user_prompt=user_query,
            final_response=synthesis_res.final_response,
            task_type=routing.task_type,
            complexity=routing.complexity,
            models_used=models_used,
            total_time_ms=total_time_ms,
            orchestration_trace={"stages": stages_data, "evaluation": eval_result.model_dump()},
            session_id=session_id,
            memory_rss_mb=req_metrics.memory_rss_mb
        )

        done_payload = {
            "session_id": session_id,
            "user_prompt": user_query,
            "final_response": synthesis_res.final_response,
            "task_type": routing.task_type,
            "sub_domain": routing.sub_domain,
            "complexity": routing.complexity,
            "is_follow_up": routing.is_follow_up,
            "models_used": models_used,
            "total_time_ms": total_time_ms,
            "routing_time_ms": routing.routing_time_ms,
            "memory_rss_mb": req_metrics.memory_rss_mb,
            "evaluation": eval_result.model_dump(),
            "synthesis_insights": synthesis_res.insights.model_dump(),
            "orchestration_stages": stages_data,
            "saved_id": record_id,
            "execution_mode": "simulated" if is_simulated else "real",
            "simulated": is_simulated,
            "is_simulated": is_simulated
        }
        yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/metrics")
def get_metrics():
    """
    Returns system telemetry, latency per model, RSS memory, and storage metrics.
    """
    return monitor.get_system_summary()

@app.get("/api/conversations")
def list_conversations(limit: int = Query(default=30, ge=1, le=100)):
    """
    Returns list of all conversation sessions with turn counts and last updated timestamp.
    """
    sessions = get_all_sessions(limit=limit)
    return {
        "count": len(sessions),
        "conversations": sessions
    }

@app.get("/api/conversations/{session_id}")
def get_conversation_turns(session_id: str, limit: int = Query(default=50, ge=1, le=100)):
    """
    Returns full chronological message history for a conversation session.
    """
    turns = get_session_history(session_id, limit=limit)
    return {
        "session_id": session_id,
        "turn_count": len(turns),
        "turns": turns
    }

@app.get("/api/history")
def get_history(limit: int = Query(default=20, ge=1, le=100)):
    """
    Retrieves previous chat conversations and orchestration traces.
    """
    records = get_recent_history(limit=limit)
    return {
        "count": len(records),
        "history": records
    }

# ==========================================
# 🦞 SYNORA AGENT ENGINE (POWERED BY CLAW CODE)
# ==========================================

@app.post("/api/agent/task")
async def run_agent_task(req: AgentTaskRequest):
    """
    Executes an autonomous coding task using Claw Code native tools (bash, edit_file, read_file, grep, etc.).
    """
    result = await agent_loop.run(
        task=req.task,
        model_id=req.model_id or "qwen2.5-coder:7b",
        max_turns=req.max_turns,
        workspace_root=req.workspace_root
    )
    return result.model_dump()

@app.post("/api/agent/stream")
async def stream_agent_task(req: AgentTaskRequest):
    """
    Streams live real-time SSE events of tool calls, bash outputs, and model reasoning steps.
    """
    generator = agent_loop.stream(
        task=req.task,
        model_id=req.model_id or "qwen2.5-coder:7b",
        max_turns=req.max_turns,
        workspace_root=req.workspace_root
    )
    return StreamingResponse(generator, media_type="text/event-stream")

@app.get("/api/agent/tools")
def get_available_tools():
    """
    Returns list of all Claw Code tools registered in SYNORA.
    """
    tools = tool_manager.get_tool_definitions()
    return {
        "tools_count": len(tools),
        "tools": tools
    }

@app.post("/api/agent/execute")
async def execute_tool_directly(req: DirectToolExecuteRequest):
    """
    Directly executes a tool and returns its output.
    """
    decision = permission_enforcer.check_tool_permission(req.tool_name, req.arguments)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason or "Permission denied")
    result = await tool_manager.dispatch(req.tool_name, req.arguments)
    return result.model_dump()

@app.get("/api/agent/permissions")
def get_permission_mode():
    return {
        "mode": permission_enforcer.mode,
        "available_modes": ["autonomous", "ask", "read_only"]
    }

@app.post("/api/agent/permissions")
def update_permission_mode(req: PermissionModeRequest):
    if req.mode not in ("autonomous", "ask", "read_only"):
        raise HTTPException(status_code=400, detail="Invalid mode. Choose 'autonomous', 'ask', or 'read_only'.")
    permission_enforcer.set_mode(req.mode)
    return {
        "success": True,
        "mode": permission_enforcer.mode
    }



@app.post("/api/claw/slash")
async def execute_slash_command(req: SlashCommandRequest):
    """
    Executes a Claw Code slash command (/doctor, /status, /diff, /review, /commit, /init, /help, etc.).
    """
    if req.workspace_root:
        slash_command_registry.set_workspace_root(req.workspace_root)
        tool_manager.set_workspace_root(req.workspace_root)
    result = await slash_command_registry.execute(req.command)
    return result.model_dump()

@app.get("/api/claw/doctor")
async def get_claw_doctor():
    """
    Runs preflight diagnostic doctor health check.
    """
    result = await slash_command_registry.cmd_doctor()
    return result.model_dump()

@app.get("/api/claw/status")
async def get_claw_status():
    """
    Returns workspace status, git repository branch, memory files, and permissions.
    """
    result = await slash_command_registry.cmd_status()
    git_res = await tool_manager.execute_git_status()
    mem_files = context_loader.discover_memory_files()
    return {
        "workspace_root": str(tool_manager.workspace_root),
        "permission_mode": permission_enforcer.mode,
        "git_status": git_res.output,
        "memory_files": mem_files,
        "status_output": result.output
    }

@app.get("/api/claw/diff")
async def get_claw_diff(path: Optional[str] = None):
    """
    Returns workspace git diff.
    """
    result = await tool_manager.execute_git_diff(path=path)
    return result.model_dump()

@app.post("/api/claw/workspace")
async def set_claw_workspace(req: WorkspacePathRequest):
    """
    Sets active workspace directory for Claw Code agent.
    """
    p = Path(req.path).resolve()
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {req.path}")
    tool_manager.set_workspace_root(str(p))
    context_loader.set_workspace_root(str(p))
    slash_command_registry.set_workspace_root(str(p))
    return {
        "success": True,
        "workspace_root": str(p)
    }
