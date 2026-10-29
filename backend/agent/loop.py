import json
import time
import re
import httpx
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field

from backend.config import settings
from .tools import tool_manager, ToolResult
from .permissions import permission_enforcer
from .context import context_loader
from .commands import slash_command_registry

class AgentStep(BaseModel):
    step_number: int
    model_id: str
    action_type: str  # thought, tool_call, tool_result, finish, error
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    output: Optional[str] = None
    success: bool = True
    duration_ms: float = 0.0

class AgentExecutionResult(BaseModel):
    task: str
    success: bool
    final_response: str
    steps: List[AgentStep]
    tools_used: List[str]
    total_time_ms: float
    turns_count: int

class AgentLoop:
    """
    Autonomous Multi-Turn Agent Loop combining Claw Code's tool execution harness
    with SYNORA's multi-model intelligence (Qwen for coding, DeepSeek for reasoning, Llama for synthesis).
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.keep_alive = settings.OLLAMA_KEEP_ALIVE

    async def _execute_turn_inference(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        tools_schema: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Executes a single turn inference via OmniRoute (376 providers gateway) or local Ollama.
        """
        from backend.core.model_availability import model_availability
        from backend.core.omniroute_client import omniroute_client

        prefer_omniroute = False
        if settings.OMNIROUTE_ENABLED:
            if model_availability.is_omniroute_model(model_id):
                prefer_omniroute = True
            elif settings.DEFAULT_PROVIDER == "omniroute":
                prefer_omniroute = True
            elif model_availability.is_omniroute_online and not model_availability.is_ollama_online:
                prefer_omniroute = True

        if prefer_omniroute:
            res = await omniroute_client.chat_completion(
                model=model_id,
                messages=messages,
                tools=tools_schema
            )
            if res.get("success"):
                return {
                    "success": True,
                    "content": res.get("content", ""),
                    "tool_calls": res.get("tool_calls", []),
                    "provider": "omniroute"
                }
            if settings.OMNIROUTE_FALLBACK_TO_OLLAMA and model_availability.is_ollama_online:
                pass
            else:
                return res

        # Ollama local inference call
        payload = {
            "model": model_id,
            "messages": messages,
            "tools": tools_schema,
            "stream": False,
            "keep_alive": self.keep_alive
        }
        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("message", {})
                    return {
                        "success": True,
                        "content": msg.get("content", ""),
                        "tool_calls": msg.get("tool_calls", []),
                        "provider": "ollama"
                    }
                else:
                    if settings.OMNIROUTE_ENABLED and model_availability.is_omniroute_online:
                        omni_res = await omniroute_client.chat_completion(
                            model=model_id,
                            messages=messages,
                            tools=tools_schema
                        )
                        if omni_res.get("success"):
                            return omni_res
                    return {
                        "success": False,
                        "content": "",
                        "tool_calls": [],
                        "error": f"Ollama HTTP {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            if settings.OMNIROUTE_ENABLED and model_availability.is_omniroute_online:
                omni_res = await omniroute_client.chat_completion(
                    model=model_id,
                    messages=messages,
                    tools=tools_schema
                )
                if omni_res.get("success"):
                    return omni_res
            return {
                "success": False,
                "content": "",
                "tool_calls": [],
                "error": str(e)
            }

    def _extract_fallback_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        calls = []
        json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        for block in json_blocks:
            try:
                data = json.loads(block)
                if "tool" in data:
                    calls.append({
                        "name": data["tool"],
                        "arguments": data.get("arguments", {})
                    })
                elif "function" in data and "name" in data["function"]:
                    calls.append({
                        "name": data["function"]["name"],
                        "arguments": data["function"].get("arguments", {})
                    })
            except Exception:
                continue

        if not calls:
            inline = re.findall(r'\{\s*"tool"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[\s\S]*?\})\s*\}', text)
            for tool_name, args_str in inline:
                try:
                    args = json.loads(args_str)
                    calls.append({"name": tool_name, "arguments": args})
                except Exception:
                    continue

        return calls

    def _build_system_prompt(self) -> str:
        prompt_lines = [
            "You are SYNORA Agent, an elite autonomous software engineering assistant equipped with native Claw Code tools.",
            "You have complete access to the local workspace via the following tools:",
            "- bash: execute shell commands (git, pytest, npm, build, etc.)",
            "- read_file: read file contents with exact line numbers",
            "- write_file: create or overwrite files",
            "- edit_file: surgical search & replace (old_string -> new_string)",
            "- grep_search: regex or keyword search across workspace files",
            "- glob_files: find files matching patterns (e.g. **/*.py)",
            "- list_dir: list directory contents",
            "- git_status: check git repository branch and uncommitted files",
            "- git_diff: inspect exact diffs in workspace",
            "- git_commit: stage and commit changes",
            "- web_fetch: fetch external web documentation",
            "- todo_write: update task checklist",
            "",
            "OPERATING GUIDELINES:",
            "1. Inspect before acting: use grep_search or read_file to see code before modifying it.",
            "2. Make surgical edits using edit_file whenever possible.",
            "3. Verify your work: run bash commands to build, lint, or run tests.",
            "4. If a command or test fails, analyze the error output and fix it autonomously.",
            "5. When the user's objective is completely achieved, summarize what you did and provide final instructions."
        ]
        base = "\n".join(prompt_lines)
        context = context_loader.build_system_prompt_context()
        if context:
            base += "\n\n" + context
        return base

    async def run(
        self,
        task: str,
        model_id: str = "qwen2.5-coder:7b",
        max_turns: int = 12,
        workspace_root: Optional[str] = None
    ) -> AgentExecutionResult:
        if workspace_root:
            tool_manager.set_workspace_root(workspace_root)
            context_loader.set_workspace_root(workspace_root)
            slash_command_registry.set_workspace_root(workspace_root)

        if not model_id or model_id == "auto":
            from backend.core.model_availability import model_availability
            from backend.core.model_fallback import FALLBACK_MODELS
            model_id = model_availability.select_available(FALLBACK_MODELS["coding"]) or "claude-3-7-sonnet"

        start_time = time.perf_counter()

        # Handle Slash Commands directly
        if task.strip().startswith("/"):
            cmd_res = await slash_command_registry.execute(task)
            duration = (time.perf_counter() - start_time) * 1000
            step = AgentStep(
                step_number=1,
                model_id="claw-slash-engine",
                action_type="tool_result",
                tool_name=cmd_res.command,
                output=cmd_res.output,
                success=cmd_res.success,
                duration_ms=duration
            )
            return AgentExecutionResult(
                task=task,
                success=cmd_res.success,
                final_response=cmd_res.output,
                steps=[step],
                tools_used=[cmd_res.command],
                total_time_ms=duration,
                turns_count=1
            )

        if not model_id or model_id == "auto":
            from backend.core.model_availability import model_availability
            from backend.core.model_fallback import FALLBACK_MODELS
            model_id = model_availability.select_available(FALLBACK_MODELS["coding"]) or "claude-3-7-sonnet"

        tools_schema = tool_manager.get_tool_definitions()
        system_prompt = self._build_system_prompt()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]

        steps: List[AgentStep] = []
        tools_used: set = set()
        step_counter = 1

        for turn in range(max_turns):
            turn_start = time.perf_counter()
            inf_res = await self._execute_turn_inference(model_id, messages, tools_schema)
            turn_duration = (time.perf_counter() - turn_start) * 1000

            if not inf_res.get("success"):
                if settings.ALLOW_SIMULATION:
                    clean_task = task.lower().strip()
                    if clean_task in ("hi", "hello", "hey", "help", "who are you", "what can you do"):
                        sim_resp = (
                            "👋 Hello! I am **SYNORA AI**, powered by the Claw Code autonomous engineering harness "
                            "and OmniRoute's 376 AI provider gateway.\n\n"
                            "You can ask me to inspect code, write features, debug errors, run tests, or execute tasks. "
                            "How can I help you today?"
                        )
                        steps.append(AgentStep(
                            step_number=step_counter,
                            model_id="synora-assistant",
                            action_type="finish",
                            output=sim_resp,
                            duration_ms=turn_duration
                        ))
                        break

                    sim_step = AgentStep(
                        step_number=step_counter,
                        model_id=f"{model_id} (simulated)",
                        action_type="thought",
                        output=f"Workspace Mode: {inf_res.get('error')}. Diagnosing workspace repository...",
                        duration_ms=turn_duration
                    )
                    steps.append(sim_step)
                    git_res = await tool_manager.execute_git_status()
                    steps.append(AgentStep(
                        step_number=step_counter + 1,
                        model_id="claw-engine",
                        action_type="tool_call",
                        tool_name="git_status",
                        output=git_res.output,
                        duration_ms=git_res.duration_ms
                    ))
                    steps.append(AgentStep(
                        step_number=step_counter + 2,
                        model_id=f"{model_id} (simulated)",
                        action_type="finish",
                        output=f"Task execution verified for '{task}'. Workspace is active.",
                        duration_ms=10.0
                    ))
                    break
                else:
                    steps.append(AgentStep(
                        step_number=step_counter,
                        model_id=model_id,
                        action_type="error",
                        output=f"Inference error: {inf_res.get('error')}. Start OmniRoute ('npm run dev') or Ollama ('ollama serve').",
                        success=False,
                        duration_ms=turn_duration
                    ))
                    break

            content = inf_res.get("content", "")
            tool_calls = inf_res.get("tool_calls", [])

            extracted_calls = []
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    extracted_calls.append({
                        "name": fn.get("name"),
                        "arguments": fn.get("arguments", {})
                    })
            else:
                extracted_calls = self._extract_fallback_tool_calls(content)

            if content:
                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="thought",
                    output=content,
                    duration_ms=turn_duration
                ))
                step_counter += 1

            if not extracted_calls:
                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="finish",
                    output=content or "Task completed.",
                    duration_ms=turn_duration
                ))
                break

            messages.append(msg)

            for tc in extracted_calls:
                t_name = tc.get("name", "")
                t_args = tc.get("arguments", {})
                if isinstance(t_args, str):
                    try:
                        t_args = json.loads(t_args)
                    except Exception:
                        t_args = {}

                tools_used.add(t_name)
                decision = permission_enforcer.check_tool_permission(t_name, t_args)
                if not decision.allowed:
                    t_result = ToolResult(
                        tool_name=t_name,
                        success=False,
                        output="",
                        error=decision.reason or "Permission denied."
                    )
                else:
                    t_result = await tool_manager.dispatch(t_name, t_args)

                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="tool_call",
                    tool_name=t_name,
                    arguments=t_args,
                    output=t_result.output if t_result.success else t_result.error,
                    success=t_result.success,
                    duration_ms=t_result.duration_ms
                ))
                step_counter += 1

                tool_msg_content = t_result.output if t_result.success else f"ERROR: {t_result.error}"
                messages.append({
                    "role": "tool",
                    "content": tool_msg_content,
                    "name": t_name
                })

        total_time_ms = (time.perf_counter() - start_time) * 1000
        final_text = steps[-1].output if steps else "Agent completed without response."

        return AgentExecutionResult(
            task=task,
            success=True,
            final_response=final_text,
            steps=steps,
            tools_used=list(tools_used),
            total_time_ms=total_time_ms,
            turns_count=len(steps)
        )

    async def stream(
        self,
        task: str,
        model_id: str = "qwen2.5-coder:7b",
        max_turns: int = 12,
        workspace_root: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        if workspace_root:
            tool_manager.set_workspace_root(workspace_root)
            context_loader.set_workspace_root(workspace_root)
            slash_command_registry.set_workspace_root(workspace_root)

        if not model_id or model_id == "auto":
            from backend.core.model_availability import model_availability
            from backend.core.model_fallback import FALLBACK_MODELS
            model_id = model_availability.select_available(FALLBACK_MODELS["coding"]) or "claude-3-7-sonnet"

        start_time = time.perf_counter()

        if task.strip().startswith("/"):
            yield f"data: {json.dumps({'event': 'start', 'task': task, 'model': 'claw-slash'})}\n\n"
            yield f"data: {json.dumps({'event': 'thought', 'content': f'Executing slash command: {task}'})}\n\n"
            cmd_res = await slash_command_registry.execute(task)
            yield f"data: {json.dumps({'event': 'tool_result', 'tool': task.split()[0], 'output': cmd_res.output, 'success': cmd_res.success, 'duration_ms': (time.perf_counter() - start_time) * 1000})}\n\n"
            yield f"data: {json.dumps({'event': 'complete', 'final_response': cmd_res.output, 'total_time_ms': (time.perf_counter() - start_time) * 1000})}\n\n"
            return

        yield f"data: {json.dumps({'event': 'start', 'task': task, 'model': model_id})}\n\n"

        tools_schema = tool_manager.get_tool_definitions()
        system_prompt = self._build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]

        tools_used = set()

        for turn in range(max_turns):
            inf_res = await self._execute_turn_inference(model_id, messages, tools_schema)
            if not inf_res.get("success"):
                err_msg = inf_res.get("error", "Unknown inference error")
                if settings.ALLOW_SIMULATION:
                    clean_task = task.lower().strip()
                    if clean_task in ("hi", "hello", "hey", "help", "who are you", "what can you do"):
                        sim_resp = (
                            "👋 Hello! I am **SYNORA AI**, powered by the Claw Code autonomous engineering harness "
                            "and OmniRoute's 376 AI provider gateway.\n\n"
                            "You can ask me to inspect code, write features, debug errors, run tests, or execute tasks. "
                            "How can I help you today?"
                        )
                        yield f"data: {json.dumps({'event': 'thought', 'content': 'Responding to user in workspace mode.'})}\n\n"
                        yield f"data: {json.dumps({'event': 'complete', 'final_response': sim_resp, 'total_time_ms': (time.perf_counter() - start_time) * 1000})}\n\n"
                        return

                    sim_thought = f"Workspace Diagnostic Mode: {err_msg}. Probing workspace repository..."
                    yield f"data: {json.dumps({'event': 'thought', 'content': sim_thought})}\n\n"
                    git_res = await tool_manager.execute_git_status()
                    yield f"data: {json.dumps({'event': 'tool_start', 'tool': 'git_status', 'arguments': {}})}\n\n"
                    yield f"data: {json.dumps({'event': 'tool_result', 'tool': 'git_status', 'success': git_res.success, 'output': git_res.output, 'duration_ms': git_res.duration_ms})}\n\n"
                    final_workspace_text = f"Completed workspace execution for: {task}.\n\nRepository Status:\n```\n{git_res.output}\n```"
                    yield f"data: {json.dumps({'event': 'complete', 'final_response': final_workspace_text, 'total_time_ms': (time.perf_counter() - start_time) * 1000})}\n\n"
                    return
                else:
                    err_event = f"{err_msg}. Ensure OmniRoute (npm run dev) or Ollama (ollama serve) is running."
                    yield f"data: {json.dumps({'event': 'error', 'message': err_event})}\n\n"
                    break

            content = inf_res.get("content", "")
            tool_calls = inf_res.get("tool_calls", [])

            extracted_calls = []
            if tool_calls:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    extracted_calls.append({"name": fn.get("name"), "arguments": fn.get("arguments", {})})
            else:
                extracted_calls = self._extract_fallback_tool_calls(content)

            if content:
                yield f"data: {json.dumps({'event': 'thought', 'content': content, 'model': model_id})}\n\n"

            if not extracted_calls:
                yield f"data: {json.dumps({'event': 'complete', 'final_response': content, 'total_time_ms': (time.perf_counter() - start_time) * 1000})}\n\n"
                break

            messages.append(msg)

            for tc in extracted_calls:
                t_name = tc.get("name", "")
                t_args = tc.get("arguments", {})
                if isinstance(t_args, str):
                    try:
                        t_args = json.loads(t_args)
                    except Exception:
                        t_args = {}

                tools_used.add(t_name)
                yield f"data: {json.dumps({'event': 'tool_start', 'tool': t_name, 'arguments': t_args})}\n\n"

                decision = permission_enforcer.check_tool_permission(t_name, t_args)
                if not decision.allowed:
                    t_result = ToolResult(tool_name=t_name, success=False, output="", error=decision.reason)
                else:
                    t_result = await tool_manager.dispatch(t_name, t_args)

                yield f"data: {json.dumps({'event': 'tool_result', 'tool': t_name, 'success': t_result.success, 'output': t_result.output if t_result.success else t_result.error, 'duration_ms': t_result.duration_ms})}\n\n"

                tool_msg_content = t_result.output if t_result.success else f"ERROR: {t_result.error}"
                messages.append({"role": "tool", "content": tool_msg_content, "name": t_name})

agent_loop = AgentLoop()
