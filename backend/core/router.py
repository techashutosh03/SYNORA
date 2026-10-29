import re
import time
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
from backend.models.registry import model_registry, ModelProfile
from backend.core.orchestrator import OrchestrationPlan, StageConfig
from backend.core.model_availability import (
    model_availability,
    NoModelsAvailableError,
    OllamaOfflineError
)
from backend.core.model_fallback import FALLBACK_MODELS

def resolve_model(task_type: str, exclude: Optional[Set[str]] = None) -> Optional[str]:
    """Selects the highest priority installed candidate model for a given task type."""
    candidates = FALLBACK_MODELS.get(
        task_type,
        FALLBACK_MODELS["general"]
    )
    return model_availability.select_available(candidates, exclude=exclude)

class RoutingDecision(BaseModel):
    task_type: str  # coding, math_reasoning, research, creative, general
    sub_domain: str
    complexity: str  # simple, medium, high
    is_follow_up: bool = False
    confidence: float
    recommended_models: List[str]
    plan: OrchestrationPlan
    routing_time_ms: float = 0.0
    is_agentic_task: bool = False

MULTILINGUAL_GREETINGS = {
    # English
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening", "how are you",
    "what's up", "whats up", "yo", "sup", "howdy",
    # Hindi / Hinglish
    "namaste", "namaskar", "pranam", "kaise ho", "kese ho", "kya haal hai", "kya hal hai",
    "kya chal raha hai", "kya kar rahe ho", "aur bhai", "hello bhai", "hi bhai",
    "kya bhai", "kya haal", "ram ram", "salaam", "adaab", "shukriya", "dhanyawad",
    "theek ho", "sab badhiya", "kya scene hai", "kya scene", "kaise hai", "kaise hain",
    "kya khabar", "kya batao"
}

def normalize_text_for_greeting(prompt: str) -> str:
    """Normalizes informal input, repeated letters (e.g. 'kyaaa' -> 'kya'), and common Hinglish typos."""
    clean = prompt.strip().lower().rstrip("!?.,~")
    # Collapse repeated letters: kyaaa -> kya, heyyy -> hey, hellooo -> hello
    clean = re.sub(r'([a-zA-Z])\1{2,}', r'\1', clean)
    # Common Hinglish typo corrections
    clean = re.sub(r'\bbhsi\b', 'bhai', clean)
    clean = re.sub(r'\bbhaai\b', 'bhai', clean)
    clean = re.sub(r'\bkyaaa+\b', 'kya', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def is_greeting(prompt: str) -> bool:
    """Detects whether a prompt is a greeting or casual multilingual conversational opening."""
    norm = normalize_text_for_greeting(prompt)
    if norm in MULTILINGUAL_GREETINGS:
        return True
    
    # Prefix matching for multi-word greetings (e.g. "namaste bhai", "hello synora", "kaise ho bhai")
    greeting_prefixes = [
        "hello", "hi", "hey", "namaste", "namaskar", "aur bhai", "kya bhai",
        "kaise ho", "kya haal", "ram ram", "salaam"
    ]
    for pfx in greeting_prefixes:
        if norm == pfx or norm.startswith(f"{pfx} ") or norm.endswith(f" {pfx}"):
            # Check there are no explicit code tokens
            code_signals = ["def", "class", "code", "python", "function", "sql", "api", "react", "bug", "algorithm"]
            if not any(sig in norm for sig in code_signals):
                return True
    return False

class Router:
    def __init__(self):
        # Multi-factor domain and sub-domain signals
        self.domain_profiles = {
            "coding": {
                "keywords": [
                    "code", "python", "javascript", "typescript", "c++", "rust", "sql", "html", "css",
                    "api", "fastapi", "react", "bug", "refactor", "function", "class", "algorithm",
                    "authentication", "jwt", "database", "git", "docker", "script", "endpoint",
                    "gui", "tkinter", "pyqt", "interface", "frontend", "backend", "test", "unittest"
                ],
                "regex_patterns": [r"def\s+\w+", r"class\s+\w+", r"```", r"import\s+\w+", r"\(\)\s*->", r"=>"],
                "default_specialist": "qwen2.5-coder:7b",
                "default_reviewer": "deepseek-r1:7b"
            },
            "math_reasoning": {
                "keywords": [
                    "math", "proof", "calculus", "algebra", "probability", "derivative", "integral",
                    "matrix", "theorem", "equation", "solve for", "combinatorics", "quantum", "physics"
                ],
                "regex_patterns": [r"\b\d+\s*[\+\-\*\/\^]\s*\d+\b", r"\b\sum\b", r"\blim_\b"],
                "default_specialist": "deepseek-r1:7b",
                "default_reviewer": "phi4:14b"
            },
            "research": {
                "keywords": [
                    "compare", "history", "difference between", "overview", "literature", "benchmark",
                    "analysis", "pros and cons", "evaluate", "case study", "contrast", "architecture"
                ],
                "regex_patterns": [r"what is the difference", r"compare and contrast", r"pros and cons"],
                "default_specialist": "mistral:7b",
                "default_reviewer": "granite3-dense:8b"
            }
        }

    def _score_model_fitness(self, model: ModelProfile, target_role: str, domain: str, complexity: str) -> float:
        """
        Multi-factor scoring algorithm to select the best model from the 30-model catalog:
        - Domain specialty match: +4.0
        - Role match (specialist/reviewer/synthesizer): +3.0
        - Installed in Ollama boost: +2.5
        - Context window headroom: +1.0
        - Parameter scale appropriateness: +1.0
        """
        score = 0.0

        # 1. Role match
        if model.recommended_role.lower() == target_role.lower():
            score += 3.0
        elif target_role == "synthesizer" and "synthesis" in [s.lower() for s in model.specialties]:
            score += 2.5
        elif target_role == "reviewer" and "reasoning" in [s.lower() for s in model.specialties]:
            score += 2.0

        # 2. Domain match
        matched_specs = [s for s in model.specialties if domain.lower() in s.lower() or s.lower() in domain.lower()]
        score += min(len(matched_specs) * 2.0, 4.0)

        # 3. Installation availability boost (prioritizes downloaded models)
        if model.is_installed:
            score += 2.5

        # 4. Context window capability
        if model.context_window >= 32768:
            score += 1.0

        # 5. Parameter tier scaling for complexity
        params_num = 0
        try:
            params_num = float(re.findall(r"\d+", model.parameters)[0])
        except Exception:
            params_num = 7.0

        if complexity == "high" and params_num >= 7.0:
            score += 1.0
        elif complexity == "simple" and params_num <= 8.0:
            score += 1.0

        return score

    def select_best_model(self, target_role: str, domain: str, complexity: str) -> str:
        """Selects the best active model using multi-factor fitness scoring."""
        active_models = model_registry.list_models(active_only=True)
        if not active_models:
            active_models = list(model_registry._models.values())

        best_model = None
        highest_score = -1.0

        for model in active_models:
            fitness = self._score_model_fitness(model, target_role, domain, complexity)
            if fitness > highest_score:
                highest_score = fitness
                best_model = model

        return best_model.id if best_model else "llama3.1:8b"

    def analyze_request(self, prompt: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes prompt and prior context to evaluate domain, sub-domain, complexity, and follow-up status.
        """
        combined_text = f"{context or ''}\n{prompt}".lower()
        prompt_lower = prompt.lower()
        words = set(re.findall(r"\b\w+\b", prompt_lower))

        # Check follow-up status
        is_follow_up = False
        if context:
            follow_up_tokens = ["now", "add", "also", "modify", "change", "it", "this", "that", "gui", "interface", "previous"]
            if any(tok in words for tok in follow_up_tokens) or len(prompt.split()) <= 10:
                is_follow_up = True

        # Score domains
        domain_scores = {}
        for domain, profile in self.domain_profiles.items():
            kw_hits = len(words.intersection(profile["keywords"]))
            pattern_hits = sum(1 for p in profile["regex_patterns"] if re.search(p, prompt, re.IGNORECASE))
            context_hits = sum(1 for kw in profile["keywords"] if kw in (context or "").lower()) * 0.4
            domain_scores[domain] = kw_hits * 1.5 + pattern_hits * 2.0 + context_hits

        # Pick primary domain
        best_domain = max(domain_scores, key=domain_scores.get)
        if domain_scores[best_domain] == 0:
            best_domain = "general"

        # Determine sub-domain
        if best_domain == "coding":
            if any(w in words for w in ["gui", "tkinter", "qt", "frontend", "interface", "react", "html"]):
                sub_domain = "ui_frontend"
            elif any(w in words for w in ["jwt", "auth", "security", "hash", "token", "password"]):
                sub_domain = "security_auth"
            else:
                sub_domain = "logic_implementation"
        elif best_domain == "math_reasoning":
            sub_domain = "derivation_proof"
        else:
            sub_domain = "analytical_synthesis"

        # Determine complexity
        prompt_len = len(prompt.split())
        has_multi_step = any(m in prompt_lower for m in ["step by step", "first", "then", "secure", "production", "complete system", "now add"])

        if is_follow_up and best_domain == "coding":
            # Follow-ups modifying existing code require specialist + reviewer to avoid breaking changes
            complexity = "high" if (has_multi_step or prompt_len > 15) else "medium"
        elif best_domain == "coding" and (has_multi_step or prompt_len > 25):
            complexity = "high"
        elif prompt_len < 12 and not has_multi_step and not is_follow_up:
            complexity = "simple"
        elif best_domain in ("coding", "math_reasoning") or prompt_len > 35:
            complexity = "medium"
        else:
            complexity = "medium"

        # Check if the user is requesting direct tool/agent execution
        agentic_indicators = [
            "create file", "write file", "edit file", "delete file", "run command",
            "execute command", "bash", "terminal", "run tests", "pytest", "npm install",
            "git status", "git commit", "fix bug in file", "read file", "grep",
            "search codebase", "clone", "compile", "build the project", "run the script"
        ]
        is_agentic_task = any(ind in prompt_lower for ind in agentic_indicators)

        return {
            "task_type": best_domain,
            "sub_domain": sub_domain,
            "complexity": complexity,
            "is_follow_up": is_follow_up,
            "confidence": min(0.75 + (domain_scores.get(best_domain, 1) * 0.05), 0.99),
            "is_agentic_task": is_agentic_task
        }

    def build_plan(
        self,
        task_type: str,
        complexity: str,
        context: Optional[str] = None,
        simulate: bool = False
    ) -> OrchestrationPlan:
        """
        Creates an orchestration plan preserving multi-model collaboration based on installed model availability.
        - 1 installed model -> Single Model Response (1 stage)
        - 2 installed models -> Two-model collaboration (2 stages)
        - 3+ installed models -> Full collaboration based on complexity (up to 3 stages)
        """
        context_guidance = ""
        if context:
            context_guidance = (
                f"Use the following prior conversation context to fulfill this request. "
                f"Preserve all previous functionality and modify/extend seamlessly:\n{context}\n\n"
            )

        # Map task_type to domain category
        if task_type == "coding":
            spec_cat = "coding"
            rev_cat = "reasoning"
            synth_cat = "synthesis"
        elif task_type in ("math_reasoning", "research"):
            spec_cat = "reasoning"
            rev_cat = "coding"
            synth_cat = "synthesis"
        else:
            spec_cat = "general"
            rev_cat = "reasoning"
            synth_cat = "synthesis"

        if simulate:
            # In simulation mode, pick candidates from fallback pools or installed
            spec_model = resolve_model(spec_cat) or FALLBACK_MODELS.get(spec_cat, ["qwen2.5-coder:7b"])[0]
            rev_model = resolve_model(rev_cat, exclude={spec_model}) or FALLBACK_MODELS.get(rev_cat, ["deepseek-r1:7b"])[0]
            synth_model = resolve_model(synth_cat, exclude={spec_model, rev_model}) or FALLBACK_MODELS.get(synth_cat, ["llama3.1:8b"])[0]
            distinct_models = [spec_model]
            if rev_model != spec_model:
                distinct_models.append(rev_model)
            if synth_model not in distinct_models:
                distinct_models.append(synth_model)
        else:
            # Real mode: strictly use installed models
            spec_model = resolve_model(spec_cat)
            if not spec_model and model_availability.installed_models:
                spec_model = list(model_availability.installed_models)[0]

            if not spec_model:
                raise NoModelsAvailableError()

            rev_model = resolve_model(rev_cat, exclude={spec_model})
            if not rev_model:
                other_models = [m for m in model_availability.installed_models if m != spec_model]
                rev_model = other_models[0] if other_models else None

            synth_model = resolve_model(synth_cat, exclude={spec_model, rev_model} if rev_model else {spec_model})
            if not synth_model:
                other_models_synth = [m for m in model_availability.installed_models if m not in {spec_model, rev_model}]
                synth_model = other_models_synth[0] if other_models_synth else None

            distinct_models = [spec_model]
            if rev_model and rev_model not in distinct_models:
                distinct_models.append(rev_model)
            if synth_model and synth_model not in distinct_models:
                distinct_models.append(synth_model)

        stages: List[StageConfig] = []
        available_count = len(distinct_models)

        # Target stage count determined by task complexity and capability benefits:
        # - simple complexity: 1 model (Direct Answer) regardless of how many models are installed
        # - medium complexity: up to 2 models (Specialist + Reviewer)
        # - high complexity: up to 3 models (Specialist + Logic Review + Synthesis)
        if complexity == "simple":
            target_stages = 1
        elif complexity == "medium":
            target_stages = min(2, available_count)
        else:
            target_stages = min(3, available_count)

        if target_stages == 1:
            chosen = distinct_models[0]
            role = "synthesizer" if complexity == "simple" else "specialist"
            stages.append(StageConfig(
                stage_name="Direct Answer" if complexity == "simple" else f"Specialist Implementation ({task_type.replace('_', ' ').title()})",
                model_id=chosen,
                role=role,
                system_prompt=f"{context_guidance}You are SYNORA AI ({chosen}). Provide a direct, authoritative, and production-grade solution."
            ))
            return OrchestrationPlan(
                task_type=task_type,
                complexity=complexity,
                stages=stages,
                synthesis_required=False
            )

        if target_stages == 2:
            m1, m2 = distinct_models[0], distinct_models[1]
            stages.append(StageConfig(
                stage_name=f"Specialist Implementation ({task_type.replace('_', ' ').title()})",
                model_id=m1,
                role="specialist",
                system_prompt=f"{context_guidance}You are the SYNORA Specialist ({m1}). Implement the requested solution with production-grade structure."
            ))
            stages.append(StageConfig(
                stage_name="Review & Refinement",
                model_id=m2,
                role="reviewer",
                system_prompt=f"You are the SYNORA Peer Reviewer ({m2}). Audit the output for correctness, security, edge cases, and deliver the final refined response."
            ))
            return OrchestrationPlan(
                task_type=task_type,
                complexity=complexity,
                stages=stages,
                synthesis_required=True
            )

        # target_stages == 3: Full collaboration
        m1, m2, m3 = distinct_models[0], distinct_models[1], distinct_models[2]
        stages.append(StageConfig(
            stage_name="Specialist Proposal",
            model_id=m1,
            role="specialist",
            system_prompt=f"{context_guidance}You are the SYNORA Specialist ({m1}). Build a comprehensive, production-ready solution."
        ))
        stages.append(StageConfig(
            stage_name="Logic & Security Audit",
            model_id=m2,
            role="reviewer",
            system_prompt=f"You are the SYNORA Security & Logic Reviewer ({m2}). Audit the solution for vulnerabilities, architectural flaws, and edge cases."
        ))
        stages.append(StageConfig(
            stage_name="Synthesis & Unification",
            model_id=m3,
            role="synthesizer",
            system_prompt=f"You are the SYNORA Synthesis Engine ({m3}). Integrate the proposal and critique into ONE definitive, cohesive response."
        ))
        return OrchestrationPlan(
            task_type=task_type,
            complexity=complexity,
            stages=stages,
            synthesis_required=True
        )

    async def route(self, prompt: str, context: Optional[str] = None, simulate: bool = False) -> RoutingDecision:
        """Determines the routing decision and execution plan for a user prompt asynchronously."""
        start = time.perf_counter()

        # Step 1: Refresh model availability from Ollama
        await model_availability.refresh()
        model_registry.sync_with_ollama(list(model_availability.installed_models))

        # Check for greeting: route to one general conversational model
        if is_greeting(prompt):
            if simulate or not model_availability.is_online or settings.ALLOW_SIMULATION:
                selected_model = resolve_model("general") or FALLBACK_MODELS["general"][0]
            else:
                selected_model = resolve_model("general")
                if selected_model is None and model_availability.installed_models:
                    selected_model = list(model_availability.installed_models)[0]
                if selected_model is None:
                    selected_model = FALLBACK_MODELS["general"][0]

            plan = OrchestrationPlan(
                task_type="general",
                complexity="simple",
                stages=[
                    StageConfig(
                        stage_name="Conversational Greeting",
                        model_id=selected_model,
                        role="synthesizer",
                        system_prompt="You are SYNORA AI, a unified multi-model intelligence. Greet the user warmly, politely, and concisely."
                    )
                ],
                synthesis_required=False
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            return RoutingDecision(
                task_type="general",
                sub_domain="greeting",
                complexity="simple",
                is_follow_up=False,
                confidence=1.0,
                recommended_models=[selected_model],
                plan=plan,
                routing_time_ms=round(elapsed_ms, 3)
            )

        # Non-greeting request validation
        if not simulate:
            if not model_availability.is_online:
                if settings.ALLOW_SIMULATION:
                    simulate = True
                else:
                    raise OllamaOfflineError(model_availability.last_error)
            elif not model_availability.installed_models:
                if settings.ALLOW_SIMULATION:
                    simulate = True
                else:
                    raise NoModelsAvailableError()

        analysis = self.analyze_request(prompt, context=context)
        plan = self.build_plan(
            analysis["task_type"],
            analysis["complexity"],
            context=context,
            simulate=simulate
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        models = [stage.model_id for stage in plan.stages]

        return RoutingDecision(
            task_type=analysis["task_type"],
            sub_domain=analysis["sub_domain"],
            complexity=analysis["complexity"],
            is_follow_up=analysis["is_follow_up"],
            confidence=analysis["confidence"],
            recommended_models=models,
            plan=plan,
            routing_time_ms=round(elapsed_ms, 3),
            is_agentic_task=analysis.get("is_agentic_task", False)
        )

router = Router()
