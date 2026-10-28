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

class AgentStep(BaseModel):
    step_number: int
    model_id: str
    action_type: str  # thought, tool_call, tool_result, finish
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

    def _extract_fallback_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses text for tool call JSON blocks if the model formats tool calls in markdown.
        Supports:
          ```json
          {"tool": "read_file", "arguments": {"path": "..."}}
          ```
          or <tool_call> tags.
        """
        calls = []
        # Pattern 1: ```json { "tool": "...", "arguments": { ... } } ```
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

        # Pattern 2: inline JSON {"tool": "...", "args": ...}
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
        base = (
            "You are SYNORA Agent, an elite autonomous software engineering assistant equipped with native tools.\n"
            "You have complete access to the local workspace via the following tools:\n"
            "- bash: execute shell commands (git, pytest, npm, build, etc.)\n"
            "- read_file: read file contents with exact line numbers\n"
            "- write_file: create or overwrite files\n"
            "- edit_file: surgical search & replace (old_string -> new_string)\n"
            "- grep_search: regex or keyword search across workspace files\n"
            "- glob_files: find files matching patterns (e.g. **/*.py)\n"
            "- list_dir: list directory contents\n\n"
            "OPERATING GUIDELINES:\n"
            "1. Inspect before acting: use grep_search or read_file to see code before modifying it.\n"
            "2. Make surgical edits using edit_file whenever possible.\n"
            "3. Verify your work: run bash commands to build, lint, or run tests.\n"
            "4. If a command or test fails, analyze the error output and fix it autonomously.\n"
            "5. When the user's objective is completely achieved, summarize what you did and provide final instructions."
        )
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
        """Executes an autonomous agent task end-to-end, returning a full execution report."""
        if workspace_root:
            tool_manager.set_workspace_root(workspace_root)
            context_loader.set_workspace_root(workspace_root)

        start_time = time.perf_counter()
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
            # 1. Call Ollama with tools
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
                    turn_duration = (time.perf_counter() - turn_start) * 1000

                    if resp.status_code != 200:
                        steps.append(AgentStep(
                            step_number=step_counter,
                            model_id=model_id,
                            action_type="error",
                            output=f"Ollama API HTTP {resp.status_code}: {resp.text}",
                            success=False,
                            duration_ms=turn_duration
                        ))
                        break

                    data = resp.json()
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    tool_calls = msg.get("tool_calls", [])

            except Exception as e:
                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="error",
                    output=f"Failed to communicate with Ollama: {str(e)}",
                    success=False,
                    duration_ms=(time.perf_counter() - turn_start) * 1000
                ))
                break

            # 2. Extract tool calls (native Ollama or text fallback)
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

            # Record model thought / message
            if content:
                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="thought",
                    output=content,
                    duration_ms=turn_duration
                ))
                step_counter += 1

            # 3. If no tool calls, the model believes it has completed the task or answered
            if not extracted_calls:
                steps.append(AgentStep(
                    step_number=step_counter,
                    model_id=model_id,
                    action_type="finish",
                    output=content or "Task completed.",
                    duration_ms=turn_duration
                ))
                break

            # Append assistant message with tool calls to history
            messages.append(msg)

            # 4. Execute all requested tool calls
            for tc in extracted_calls:
                t_name = tc.get("name", "")
                t_args = tc.get("arguments", {})
                if isinstance(t_args, str):
                    try:
                        t_args = json.loads(t_args)
                    except Exception:
                        t_args = {}

                tools_used.add(t_name)

                # Permission Check
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

                # Feed tool result back into context
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
        """
        Streams real-time SSE events for live visualization in SYNORA's frontend.
        Events: start, thought, tool_start, tool_result, error, complete.
        """
        if workspace_root:
            tool_manager.set_workspace_root(workspace_root)
            context_loader.set_workspace_root(workspace_root)

        start_time = time.perf_counter()
        yield f"data: {json.dumps({'event': 'start', 'task': task, 'model': model_id})}\n\n"

        tools_schema = tool_manager.get_tool_definitions()
        system_prompt = self._build_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]

        tools_used = set()

        for turn in range(max_turns):
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
                    if resp.status_code != 200:
                        yield f"data: {json.dumps({'event': 'error', 'message': f'Ollama HTTP {resp.status_code}'})}\n\n"
                        break

                    data = resp.json()
                    msg = data.get("message", {})
                    content = msg.get("content", "")
                    tool_calls = msg.get("tool_calls", [])

            except Exception as e:
                yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"
                break

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
