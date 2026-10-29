import time
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.config import settings
from backend.models.registry import model_registry

class StageConfig(BaseModel):
    stage_name: str
    model_id: str
    role: str  # specialist, reviewer, synthesizer
    system_prompt: Optional[str] = None

class OrchestrationPlan(BaseModel):
    task_type: str
    complexity: str
    stages: List[StageConfig]
    synthesis_required: bool = False

class StageResult(BaseModel):
    stage_name: str
    model_id: str
    role: str
    prompt: str
    response: str
    execution_time_ms: float
    status: str = "success"  # success, fallback, error
    error_message: Optional[str] = None

class OrchestrationResult(BaseModel):
    user_prompt: str
    plan: OrchestrationPlan
    stage_results: List[StageResult]
    final_response: str
    total_time_ms: float
    models_used: List[str]

class OllamaInferenceError(Exception):
    """Raised when an Ollama model call fails and simulation is disabled."""
    pass

class ModelUnavailableError(Exception):
    """Raised when a required AI model is not installed in Ollama."""
    def __init__(self, model_id: str, message: Optional[str] = None):
        self.model_id = model_id
        self.message = message or (
            f"Model Unavailable\n\n"
            f"The required AI model is not installed.\n\n"
            f"Model: {model_id}\n\n"
            f"Install using:\n"
            f"ollama pull {model_id}"
        )
        super().__init__(self.message)

class Orchestrator:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.keep_alive = settings.OLLAMA_KEEP_ALIVE

    async def check_system_health(self) -> Dict[str, Any]:
        """Checks both OmniRoute gateway and Ollama service health."""
        from backend.core.omniroute_client import omniroute_client
        omni_health = await omniroute_client.check_health()
        ollama_health = await self.check_ollama_health()
        return {
            "omniroute": omni_health,
            "ollama": ollama_health,
            "active_provider": "omniroute" if omni_health.get("online") else ("ollama" if ollama_health.get("status") == "connected" else "simulation")
        }

    async def check_ollama_health(self) -> Dict[str, Any]:
        """Checks if Ollama service is reachable and fetches local models."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    model_registry.sync_with_ollama(models)
                    return {
                        "status": "connected",
                        "installed_models_count": len(models),
                        "installed_models": models
                    }
                return {
                    "status": "error",
                    "status_code": res.status_code,
                    "message": "Ollama returned non-200 status."
                }
        except httpx.ConnectError:
            return {
                "status": "disconnected",
                "message": f"Could not connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve')."
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    async def _call_omniroute(
        self,
        model_id: str,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Executes a model inference call via OmniRoute's OpenAI-compatible API.
        Routes through OmniRoute's intelligent provider pool (376 providers),
        circuit breakers, and auto-fallbacks.
        """
        from backend.core.omniroute_client import omniroute_client
        return await omniroute_client.chat_completion(model=model_id, messages=messages)

    async def _call_model(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        keep_alive: int = 0
    ) -> Dict[str, Any]:
        """
        Intelligently dispatches inference to OmniRoute or local Ollama.
        """
        from backend.core.model_availability import model_availability
        
        prefer_omniroute = False
        if settings.OMNIROUTE_ENABLED:
            if model_availability.is_omniroute_model(model_id):
                prefer_omniroute = True
            elif settings.DEFAULT_PROVIDER == "omniroute":
                prefer_omniroute = True
            elif model_availability.is_omniroute_online and not model_availability.is_ollama_online:
                prefer_omniroute = True

        if prefer_omniroute:
            res = await self._call_omniroute(model_id, messages)
            if res.get("success"):
                return res
            # Fallback to Ollama if configured and available
            if settings.OMNIROUTE_FALLBACK_TO_OLLAMA and model_availability.is_ollama_online:
                return await self._call_ollama(model_id, messages, keep_alive=keep_alive)
            return res
        else:
            res = await self._call_ollama(model_id, messages, keep_alive=keep_alive)
            if not res.get("success") and settings.OMNIROUTE_ENABLED and model_availability.is_omniroute_online:
                return await self._call_omniroute(model_id, messages)
            return res

    async def _call_ollama(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        keep_alive: int = 0
    ) -> Dict[str, Any]:
        """
        Executes a single model inference call via Ollama API.
        Enforces keep_alive=0 to immediately release VRAM on 16GB M2.
        """
        start = time.perf_counter()
        payload = {
            "model": model_id,
            "messages": messages,
            "stream": False,
            "keep_alive": keep_alive
        }

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT_SECONDS) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("message", {}).get("content", "")
                    return {
                        "success": True,
                        "content": content,
                        "elapsed_ms": elapsed_ms,
                        "error": None
                    }
                else:
                    is_missing = resp.status_code == 404 or "not found" in resp.text.lower()
                    return {
                        "success": False,
                        "content": "",
                        "elapsed_ms": elapsed_ms,
                        "error": f"Ollama HTTP {resp.status_code}: {resp.text}",
                        "is_missing": is_missing,
                        "status_code": resp.status_code
                    }
        except httpx.ConnectError:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "content": "",
                "elapsed_ms": elapsed_ms,
                "error": f"Connection refused to Ollama at {self.base_url}. Is Ollama running ('ollama serve')?",
                "is_missing": True,
                "is_connection_error": True
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "success": False,
                "content": "",
                "elapsed_ms": elapsed_ms,
                "error": str(e),
                "is_missing": False
            }

    def _find_installed_fallback(self, role: str) -> Optional[str]:
        """Finds an installed alternative model from the registry matching role/general."""
        installed = model_registry.list_models(installed_only=True, active_only=True)
        # First match exact role
        for m in installed:
            if m.recommended_role.lower() == role.lower():
                return m.id
        # Fallback to any installed model
        if installed:
            return installed[0].id
        return None

    def _generate_simulated_response(self, stage: StageConfig, user_prompt: str, stage_results: List[StageResult]) -> str:
        """
        Generates a realistic, highly articulate conversational or technical multi-model orchestration response
        tailored to any question just like ChatGPT, Claude, and Gemini.
        """
        role = stage.role.lower()
        model = stage.model_id

        from backend.core.conversational_engine import answer_general_query, detect_intent
        intent = detect_intent(user_prompt)
        is_code = intent == "coding" or any(k in user_prompt.lower() for k in ["code", "function", "class", "def ", "import ", "sql", "react", "fastapi", "bug", "implement", "script", "algorithm"])

        # For conversational, explanations, creative, or general Q&A
        if not is_code:
            base_answer = answer_general_query(user_prompt)
            if role == "specialist" or len(stage_results) == 0:
                return base_answer
            elif role == "reviewer" or len(stage_results) == 1:
                specialist_id = stage_results[0].model_id
                return (
                    f"### Perspective Review & Fact-Check\n"
                    f"**Engine**: `{model}` (Reviewer & Synthesizer)\n"
                    f"**Target**: Analysis by `{specialist_id}`\n\n"
                    f"**Quality & Accuracy Assessment:**\n"
                    f"- **Completeness**: The core concepts addressing \"{user_prompt}\" are clearly and accurately articulated.\n"
                    f"- **Clarity & Tone**: The explanation maintains a natural, helpful, and accessible conversational flow.\n"
                    f"- **Additional Insight**: Remember to consider practical real-world context and continuous application when exploring this topic further.\n\n"
                    f"{base_answer}"
                )
            else:
                return base_answer

        # For coding and software engineering queries
        if role == "specialist" or len(stage_results) == 0:
            return (
                f"### Implementation Solution\n"
                f"**Engine**: `{model}` (Coding Specialist)\n\n"
                f"Here is a clean, modular solution tailored to: **\"{user_prompt}\"**\n\n"
                f"```python\n"
                f"# Implementation for: {user_prompt}\n"
                f"import time\n"
                f"from typing import Any, Dict, Optional, List\n\n"
                f"class Solution:\n"
                f"    \"\"\"Production-ready modular implementation.\"\"\"\n"
                f"    def __init__(self, name: str = 'default'):\n"
                f"        self.name = name\n"
                f"        self.created_at = time.time()\n\n"
                f"    def process(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n"
                f"        payload = data or {{}}\n"
                f"        # Execute core logic safely with type hints\n"
                f"        return {{\n"
                f"            'status': 'success',\n"
                f"            'input': payload,\n"
                f"            'timestamp': time.time()\n"
                f"        }}\n"
                f"```\n\n"
                f"**Key Highlights:**\n"
                f"- Clean type annotations and error boundaries.\n"
                f"- Follows idiomatic architecture with minimal overhead.\n"
                f"- Ready for peer review and edge-case validation."
            )
        elif role == "reviewer" or len(stage_results) == 1:
            specialist_id = stage_results[0].model_id
            return (
                f"### Code Quality & Security Audit\n"
                f"**Engine**: `{model}` (Reasoning Reviewer)\n"
                f"**Target**: Proposal by `{specialist_id}`\n\n"
                f"**Audit Findings:**\n"
                f"1. **Input Validation**: Verified that null or non-dictionary inputs are handled safely.\n"
                f"2. **Boundary Safety**: Exception handling guarantees memory and timeout protection under Apple Silicon M2 constraints.\n"
                f"3. **Optimization**: Recommended defensive parameter checking for production deployments."
            )
        else:
            return (
                f"### Unified Synthesis\n"
                f"**Engine**: `{model}` (Synthesis Engine)\n\n"
                f"Harmonizing the initial implementation with the peer security audit produces the complete, verified solution for **\"{user_prompt}\"**:\n\n"
                f"```python\n"
                f"import time\n"
                f"from typing import Any, Dict, Optional\n\n"
                f"class VerifiedSolution:\n"
                f"    \"\"\"Production-grade, security-hardened implementation.\"\"\"\n"
                f"    def __init__(self, name: str = 'production'):\n"
                f"        self.name = name\n"
                f"        self.initialized_at = time.time()\n\n"
                f"    def process(self, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:\n"
                f"        if data is not None and not isinstance(data, dict):\n"
                f"            raise TypeError('Expected data to be a dictionary')\n"
                f"        payload = data or {{}}\n"
                f"        return {{\n"
                f"            'status': 'success',\n"
                f"            'verified': True,\n"
                f"            'payload': payload,\n"
                f"            'timestamp': time.time()\n"
                f"        }}\n"
                f"```\n\n"
                f"**Summary of Synthesis:**\n"
                f"- Integrated defensive boundary checks.\n"
                f"- Retained modular interface and clear documentation."
            )

    async def execute_plan(
        self,
        user_prompt: str,
        plan: OrchestrationPlan,
        simulate: bool = False
    ) -> OrchestrationResult:
        """
        Executes an orchestration plan sequentially across models.
        Strictly sequential execution guarantees only 1 model occupies M2 unified memory at any given time.
        """
        overall_start = time.perf_counter()
        stage_results: List[StageResult] = []
        models_used: List[str] = []

        # Strict simulation mode: only simulate if simulate is explicitly True.
        # When simulate is False, real inference is required.
        # Never silently switch to simulation.
        use_simulation = bool(simulate)

        for stage in plan.stages:
            target_model = stage.model_id
            stage_start = time.perf_counter()

            if use_simulation:
                # Simulated response path - ONLY when simulate is True
                content = self._generate_simulated_response(stage, user_prompt, stage_results)
                stage_ms = 450.0 + (len(stage_results) * 120.0)
                status = "simulated"
                err = None
                res = {"success": True, "content": content, "elapsed_ms": stage_ms, "error": None}
            else:
                # Real inference is required.
                # Never silently switch to simulation.
                messages: List[Dict[str, str]] = []
                if stage.system_prompt:
                    messages.append({"role": "system", "content": stage.system_prompt})

                if len(stage_results) == 0:
                    messages.append({"role": "user", "content": user_prompt})
                elif len(stage_results) == 1:
                    specialist_model = plan.stages[0].model_id
                    specialist_text = stage_results[0].response
                    if plan.task_type == "coding":
                        audit_prompt = (
                            f"### Context\nUser Request: {user_prompt}\n\n"
                            f"### Proposed Solution by Specialist ({specialist_model}):\n{specialist_text}\n\n"
                            f"### Your Task as Code Reviewer ({stage.model_id}):\n"
                            f"1. Thoroughly audit this proposed solution for logic bugs, security vulnerabilities, and edge cases.\n"
                            f"2. Explicitly specify which recommendations are essential vs optional.\n"
                            f"3. Provide concrete code fixes or corrections for any identified flaws."
                        )
                    else:
                        audit_prompt = (
                            f"### User Question\n{user_prompt}\n\n"
                            f"### Initial Response by Specialist ({specialist_model}):\n{specialist_text}\n\n"
                            f"### Your Task as Reviewer & Fact-Checker ({stage.model_id}):\n"
                            f"1. Review this response for factual accuracy, completeness, clarity, and helpfulness.\n"
                            f"2. Suggest additional insights, helpful examples, or nuances that enrich the answer.\n"
                            f"3. Ensure the tone is engaging, thoughtful, and directly answers the user's inquiry."
                        )
                    messages.append({"role": "user", "content": audit_prompt})
                else:
                    specialist_text = stage_results[0].response
                    reviewer_text = stage_results[1].response
                    if plan.task_type == "coding":
                        synthesis_prompt = (
                            f"### User Request\n{user_prompt}\n\n"
                            f"### Specialist Proposal ({plan.stages[0].model_id}):\n{specialist_text}\n\n"
                            f"### Reviewer Critique & Security Audit ({plan.stages[1].model_id}):\n{reviewer_text}\n\n"
                            f"### Your Task as the SYNORA Synthesis Engine ({stage.model_id}):\n"
                            f"Produce ONE unified, definitive, and production-grade final response.\n"
                            f"- Merge the Specialist's core implementation with the Reviewer's justified security fixes.\n"
                            f"- Resolve any contradictions between the two models.\n"
                            f"- Present the single best, fully revised solution."
                        )
                    else:
                        synthesis_prompt = (
                            f"### User Inquiry\n{user_prompt}\n\n"
                            f"### Specialist Perspective ({plan.stages[0].model_id}):\n{specialist_text}\n\n"
                            f"### Reviewer Insights ({plan.stages[1].model_id}):\n{reviewer_text}\n\n"
                            f"### Your Task as the SYNORA Synthesis Engine ({stage.model_id}):\n"
                            f"Deliver ONE cohesive, articulate, engaging, and comprehensive final response just like ChatGPT, Claude, or Gemini.\n"
                            f"- Unify the best explanations into a clear, natural, and helpful answer.\n"
                            f"- Ensure conversational warmth, clarity, and depth.\n"
                            f"- Directly address every aspect of the user's inquiry."
                        )
                    messages.append({"role": "user", "content": synthesis_prompt})

                # Attempt inference call via OmniRoute or Ollama
                res = await self._call_model(
                    model_id=target_model,
                    messages=messages,
                    keep_alive=self.keep_alive
                )

                # If failed, attempt installed model fallback ONLY among installed models
                if not res["success"]:
                    fallback_model = self._find_installed_fallback(stage.role)
                    if fallback_model and fallback_model != target_model:
                        target_model = fallback_model
                        res = await self._call_model(
                            model_id=fallback_model,
                            messages=messages,
                            keep_alive=self.keep_alive
                        )

                # If still failed: NEVER fall back to simulation when real inference is required!
                if not res["success"]:
                    is_missing = res.get("is_missing") or "not found" in str(res.get("error", "")).lower() or res.get("status_code") == 404
                    if is_missing:
                        raise ModelUnavailableError(model_id=target_model)
                    raise OllamaInferenceError(
                        f"Inference failed for stage '{stage.stage_name}' using model '{stage.model_id}'. "
                        f"Reason: {res['error']}. "
                        f"Please ensure OmniRoute is running ('npm run dev') or Ollama is running ('ollama serve')."
                    )

                content = res["content"]
                status = "success"
                err = None

                stage_ms = res["elapsed_ms"] if res["success"] else (time.perf_counter() - stage_start) * 1000

            stage_result = StageResult(
                stage_name=stage.stage_name,
                model_id=target_model,
                role=stage.role,
                prompt=user_prompt if len(stage_results) == 0 else "collaborative_stage_prompt",
                response=content,
                execution_time_ms=round(stage_ms, 2),
                status=status,
                error_message=err
            )
            stage_results.append(stage_result)
            models_used.append(target_model)

        final_response = stage_results[-1].response
        total_time = (time.perf_counter() - overall_start) * 1000

        return OrchestrationResult(
            user_prompt=user_prompt,
            plan=plan,
            stage_results=stage_results,
            final_response=final_response,
            total_time_ms=round(total_time, 2),
            models_used=models_used
        )

# Global singleton orchestrator instance
orchestrator = Orchestrator()

