from typing import Optional, List, Dict
from pydantic import BaseModel, Field, computed_field

class ModelProfile(BaseModel):
    id: str = Field(..., description="Model identifier, e.g. qwen2.5-coder:7b or claude-3-7-sonnet")
    name: str = Field(..., description="Human-readable model name")
    family: str = Field(..., description="Model family, e.g. Qwen, DeepSeek, Llama, Anthropic, OpenAI")
    parameters: str = Field(..., description="Parameter size, e.g. 7B, 8B, 14B, Cloud")
    specialties: List[str] = Field(default_factory=list, description="Specialized domains, e.g. ['coding', 'python']")
    recommended_role: str = Field(..., description="Primary orchestration role: specialist, reviewer, synthesizer, router, evaluator")
    context_window: int = Field(default=8192, description="Maximum context window tokens")
    is_installed: bool = Field(default=False, description="Whether currently available in local Ollama or OmniRoute")
    is_active: bool = Field(default=True, description="Whether enabled in SYNORA routing pool")
    tier: int = Field(default=2, description="0: OmniRoute Cloud Flagship, 1: Core Milestone, 2: Popular Specialists, 3: Advanced")
    provider: str = Field(default="ollama", description="Provider origin: ollama, omniroute, cloud")

    @computed_field
    @property
    def specialty(self) -> str:
        return self.specialties[0] if self.specialties else "general"

class ModelRegistry:
    def __init__(self):
        self._models: Dict[str, ModelProfile] = {}
        self._load_default_catalog()

    def _load_default_catalog(self):
        """Initializes catalog of OmniRoute cloud flagships and 30 open-weight models."""
        catalog = [
            # Tier 0: OmniRoute Cloud Flagship Models (376 Providers Gateway)
            ModelProfile(
                id="claude-3-7-sonnet",
                name="Claude 3.7 Sonnet (OmniRoute)",
                family="Anthropic",
                parameters="Hybrid Reasoning/Code",
                specialties=["coding", "refactoring", "architecture", "python", "typescript", "surgical-edits"],
                recommended_role="specialist",
                context_window=200000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="claude-3-5-sonnet",
                name="Claude 3.5 Sonnet (OmniRoute)",
                family="Anthropic",
                parameters="Flagship",
                specialties=["coding", "refactoring", "debugging", "python", "javascript"],
                recommended_role="specialist",
                context_window=200000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="gpt-4o",
                name="OpenAI GPT-4o (OmniRoute)",
                family="OpenAI",
                parameters="Multimodal Flagship",
                specialties=["synthesis", "general", "instruction", "writing", "analysis"],
                recommended_role="synthesizer",
                context_window=128000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="deepseek-reasoner",
                name="DeepSeek R1 Reasoner (OmniRoute)",
                family="DeepSeek",
                parameters="671B MoE",
                specialties=["reasoning", "logic", "review", "math", "security-audit"],
                recommended_role="reviewer",
                context_window=64000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="deepseek-chat",
                name="DeepSeek V3 (OmniRoute)",
                family="DeepSeek",
                parameters="671B MoE",
                specialties=["coding", "algorithms", "refactoring", "general"],
                recommended_role="specialist",
                context_window=64000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="gemini-2.0-flash",
                name="Google Gemini 2.0 Flash (OmniRoute)",
                family="Google",
                parameters="Ultra-Fast",
                specialties=["routing", "fast-classification", "synthesis", "multimodal"],
                recommended_role="router",
                context_window=1000000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="qwen-2.5-coder-32b",
                name="Qwen 2.5 Coder 32B (OmniRoute)",
                family="Qwen",
                parameters="32B",
                specialties=["coding", "refactoring", "debugging", "python", "backend"],
                recommended_role="specialist",
                context_window=32768,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="llama-3.3-70b",
                name="Meta Llama 3.3 70B (OmniRoute)",
                family="Llama",
                parameters="70B",
                specialties=["synthesis", "general", "explanation", "analysis"],
                recommended_role="synthesizer",
                context_window=128000,
                tier=0,
                provider="omniroute"
            ),
            ModelProfile(
                id="omniroute-auto",
                name="OmniRoute Auto-Combo Router",
                family="OmniRoute",
                parameters="Dynamic Ensemble",
                specialties=["auto-fallback", "combo-routing", "cost-optimized", "resilience"],
                recommended_role="router",
                context_window=128000,
                tier=0,
                provider="omniroute"
            ),

            # Tier 1: Core Milestone Trio & Fast Routers
            ModelProfile(
                id="qwen2.5-coder:7b",
                name="Qwen 2.5 Coder 7B",
                family="Qwen",
                parameters="7B",
                specialties=["coding", "refactoring", "debugging", "python", "javascript"],
                recommended_role="specialist",
                context_window=32768,
                tier=1
            ),
            ModelProfile(
                id="deepseek-r1:7b",
                name="DeepSeek R1 7B",
                family="DeepSeek",
                parameters="7B",
                specialties=["reasoning", "logic", "review", "math", "analysis"],
                recommended_role="reviewer",
                context_window=65536,
                tier=1
            ),
            ModelProfile(
                id="llama3.1:8b",
                name="Meta Llama 3.1 8B",
                family="Llama",
                parameters="8B",
                specialties=["synthesis", "general", "explanation", "writing"],
                recommended_role="synthesizer",
                context_window=131072,
                tier=1
            ),
            ModelProfile(
                id="llama3.2:3b",
                name="Meta Llama 3.2 3B",
                family="Llama",
                parameters="3B",
                specialties=["routing", "fast-classification", "summarization"],
                recommended_role="router",
                context_window=131072,
                tier=1
            ),
            ModelProfile(
                id="llama3.2:1b",
                name="Meta Llama 3.2 1B",
                family="Llama",
                parameters="1B",
                specialties=["conversation", "multilingual", "fast-chat", "synthesis", "general", "edge-routing"],
                recommended_role="synthesizer",
                context_window=131072,
                tier=1
            ),

            # Tier 2: Deep Coding & Reasoning Specialists
            ModelProfile(
                id="deepseek-coder:6.7b",
                name="DeepSeek Coder 6.7B",
                family="DeepSeek",
                parameters="6.7B",
                specialties=["coding", "algorithms", "syntax"],
                recommended_role="specialist",
                context_window=16384,
                tier=2
            ),
            ModelProfile(
                id="qwen2.5:7b",
                name="Qwen 2.5 7B",
                family="Qwen",
                parameters="7B",
                specialties=["multilingual", "instruction", "knowledge"],
                recommended_role="specialist",
                context_window=32768,
                tier=2
            ),
            ModelProfile(
                id="phi4:14b",
                name="Microsoft Phi-4 14B",
                family="Phi",
                parameters="14B",
                specialties=["math", "stem", "dense-reasoning"],
                recommended_role="specialist",
                context_window=16384,
                tier=2
            ),
            ModelProfile(
                id="phi3.5:3.8b",
                name="Microsoft Phi-3.5 3.8B",
                family="Phi",
                parameters="3.8B",
                specialties=["reasoning", "compact-logic", "fast-qa"],
                recommended_role="specialist",
                context_window=128000,
                tier=2
            ),
            ModelProfile(
                id="mistral:7b",
                name="Mistral 7B Instruct",
                family="Mistral",
                parameters="7B",
                specialties=["instruction-following", "summarization", "writing"],
                recommended_role="synthesizer",
                context_window=32768,
                tier=2
            ),
            ModelProfile(
                id="codellama:7b",
                name="Code Llama 7B",
                family="Llama",
                parameters="7B",
                specialties=["coding", "unit-testing", "code-completion"],
                recommended_role="specialist",
                context_window=16384,
                tier=2
            ),
            ModelProfile(
                id="gemma2:9b",
                name="Google Gemma 2 9B",
                family="Gemma",
                parameters="9B",
                specialties=["structured-synthesis", "factual-clarity", "dialogue"],
                recommended_role="synthesizer",
                context_window=8192,
                tier=2
            ),
            ModelProfile(
                id="gemma2:2b",
                name="Google Gemma 2 2B",
                family="Gemma",
                parameters="2B",
                specialties=["evaluation", "validation", "compact-qa"],
                recommended_role="evaluator",
                context_window=8192,
                tier=2
            ),
            ModelProfile(
                id="starcoder2:7b",
                name="StarCoder2 7B",
                family="StarCoder",
                parameters="7B",
                specialties=["polyglot-coding", "repository-context", "low-level-code"],
                recommended_role="specialist",
                context_window=16384,
                tier=2
            ),
            ModelProfile(
                id="granite3-dense:8b",
                name="IBM Granite 3 Dense 8B",
                family="Granite",
                parameters="8B",
                specialties=["enterprise", "governance", "factual-retrieval"],
                recommended_role="specialist",
                context_window=8192,
                tier=2
            ),
            ModelProfile(
                id="granite-code:8b",
                name="IBM Granite Code 8B",
                family="Granite",
                parameters="8B",
                specialties=["code-explanation", "enterprise-software", "sql"],
                recommended_role="specialist",
                context_window=8192,
                tier=2
            ),

            # Tier 3: Advanced Domain & High-Fidelity Extended Models
            ModelProfile(
                id="command-r:35b",
                name="Cohere Command R 35B",
                family="Command",
                parameters="35B",
                specialties=["rag", "multilingual", "complex-search"],
                recommended_role="synthesizer",
                context_window=128000,
                tier=3
            ),
            ModelProfile(
                id="nemotron-mini:4b",
                name="NVIDIA Nemotron Mini 4B",
                family="Nemotron",
                parameters="4B",
                specialties=["synthetic-evaluation", "math", "instruction"],
                recommended_role="evaluator",
                context_window=8192,
                tier=3
            ),
            ModelProfile(
                id="yi:9b",
                name="01.AI Yi 9B",
                family="Yi",
                parameters="9B",
                specialties=["bilingual", "reading-comprehension", "creative"],
                recommended_role="specialist",
                context_window=32768,
                tier=3
            ),
            ModelProfile(
                id="solar:10.7b",
                name="Upstage Solar 10.7B",
                family="Solar",
                parameters="10.7B",
                specialties=["general-fluency", "conversation", "summarization"],
                recommended_role="synthesizer",
                context_window=8192,
                tier=3
            ),
            ModelProfile(
                id="wizardlm2:7b",
                name="WizardLM-2 7B",
                family="WizardLM",
                parameters="7B",
                specialties=["multi-turn-instruction", "complex-prompts"],
                recommended_role="specialist",
                context_window=32768,
                tier=3
            ),
            ModelProfile(
                id="falcon2:11b",
                name="TII Falcon 2 11B",
                family="Falcon",
                parameters="11B",
                specialties=["knowledge-dense", "technical-writing"],
                recommended_role="specialist",
                context_window=8192,
                tier=3
            ),
            ModelProfile(
                id="orca2:7b",
                name="Microsoft Orca 2 7B",
                family="Orca",
                parameters="7B",
                specialties=["subtask-decomposition", "step-by-step-explanation"],
                recommended_role="reviewer",
                context_window=4096,
                tier=3
            ),
            ModelProfile(
                id="mathstral:7b",
                name="Mistral Mathstral 7B",
                family="Mistral",
                parameters="7B",
                specialties=["advanced-math", "calculus", "scientific-computing"],
                recommended_role="specialist",
                context_window=32768,
                tier=3
            ),
            ModelProfile(
                id="codegemma:7b",
                name="Google CodeGemma 7B",
                family="Gemma",
                parameters="7B",
                specialties=["code-completion", "syntax-verification"],
                recommended_role="specialist",
                context_window=8192,
                tier=3
            ),
            ModelProfile(
                id="deepseek-llm:7b",
                name="DeepSeek LLM 7B",
                family="DeepSeek",
                parameters="7B",
                specialties=["general-qa", "historical-knowledge", "creative"],
                recommended_role="specialist",
                context_window=8192,
                tier=3
            ),
            ModelProfile(
                id="qwen2.5-math:7b",
                name="Qwen 2.5 Math 7B",
                family="Qwen",
                parameters="7B",
                specialties=["math-proofs", "symbolic-logic", "competition-math"],
                recommended_role="specialist",
                context_window=4096,
                tier=3
            ),
            ModelProfile(
                id="hermes3:8b",
                name="Nous Hermes 3 8B",
                family="Hermes",
                parameters="8B",
                specialties=["roleplay", "agentic-actions", "unfiltered-reasoning"],
                recommended_role="specialist",
                context_window=128000,
                tier=3
            ),
            ModelProfile(
                id="internlm2:7b",
                name="InternLM2 7B",
                family="InternLM",
                parameters="7B",
                specialties=["long-context-analysis", "data-extraction"],
                recommended_role="specialist",
                context_window=32768,
                tier=3
            ),
            ModelProfile(
                id="smollm2:1.7b",
                name="Hugging Face SmolLM2 1.7B",
                family="SmolLM",
                parameters="1.7B",
                specialties=["micro-routing", "quick-filter", "json-extraction"],
                recommended_role="router",
                context_window=8192,
                tier=3
            )
        ]
        for m in catalog:
            self._models[m.id] = m

    def register(self, profile: ModelProfile):
        self._models[profile.id] = profile

    def get(self, model_id: str) -> Optional[ModelProfile]:
        return self._models.get(model_id)

    def list_models(
        self,
        specialty: Optional[str] = None,
        role: Optional[str] = None,
        installed_only: bool = False,
        active_only: bool = False
    ) -> List[ModelProfile]:
        res = list(self._models.values())
        if specialty:
            res = [m for m in res if specialty.lower() in [s.lower() for s in m.specialties]]
        if role:
            res = [m for m in res if m.recommended_role.lower() == role.lower()]
        if installed_only:
            res = [m for m in res if m.is_installed]
        if active_only:
            res = [m for m in res if m.is_active]
        return res

    def get_candidate_models(self, domain: str, role: str) -> List[ModelProfile]:
        """Returns ordered candidates for a specific domain and role."""
        candidates = [
            m for m in self._models.values()
            if m.is_active and (role.lower() == m.recommended_role.lower() or domain.lower() in [s.lower() for s in m.specialties])
        ]
        # Sort by installed status first, then tier
        candidates.sort(key=lambda m: (not m.is_installed, m.tier))
        return candidates

    def sync_with_ollama(self, local_model_tags: List[str]):
        """Marks which models from the catalog are installed locally in Ollama."""
        normalized_tags = {tag.strip().lower() for tag in local_model_tags}
        # Also handle tags without tag versions (e.g., 'qwen2.5-coder' matching 'qwen2.5-coder:7b')
        for model_id, profile in self._models.items():
            base_id = model_id.split(":")[0].lower()
            is_found = (model_id.lower() in normalized_tags) or any(
                tag == base_id or tag.startswith(f"{base_id}:") for tag in normalized_tags
            )
            profile.is_installed = is_found

    def sync_with_omniroute(self, omniroute_model_ids: List[str]):
        """Marks OmniRoute models as installed and auto-registers new ones dynamically."""
        norm_map = {m.strip().lower(): m.strip() for m in omniroute_model_ids}
        for model_id, profile in self._models.items():
            if profile.provider == "omniroute" or model_id.lower() in norm_map or any(base in model_id.lower() for base in norm_map):
                profile.is_installed = True

        # Dynamically register any models discovered from OmniRoute
        for raw_id in omniroute_model_ids:
            clean_id = raw_id.strip()
            if clean_id not in self._models:
                lower = clean_id.lower()
                role = "general"
                family = "Cloud"
                specialties = ["omniroute", "cloud"]
                if any(k in lower for k in ["code", "coder", "claude", "qwen"]):
                    role = "specialist"
                    specialties.extend(["coding", "refactoring"])
                elif any(k in lower for k in ["reason", "r1", "o1", "o3", "deepseek"]):
                    role = "reviewer"
                    specialties.extend(["reasoning", "logic"])
                elif any(k in lower for k in ["gpt-4", "llama", "gemini"]):
                    role = "synthesizer"
                    specialties.extend(["synthesis", "general"])

                if "claude" in lower:
                    family = "Anthropic"
                elif "gpt" in lower or "o1" in lower or "o3" in lower:
                    family = "OpenAI"
                elif "gemini" in lower:
                    family = "Google"
                elif "deepseek" in lower:
                    family = "DeepSeek"
                elif "llama" in lower:
                    family = "Meta"
                elif "qwen" in lower:
                    family = "Qwen"

                self._models[clean_id] = ModelProfile(
                    id=clean_id,
                    name=clean_id,
                    family=family,
                    parameters="Cloud/API",
                    specialties=specialties,
                    recommended_role=role,
                    context_window=128000,
                    is_installed=True,
                    is_active=True,
                    tier=0,
                    provider="omniroute"
                )

    def set_active_models(self, model_ids: List[str]):
        """Selects which models are enabled in the active pool."""
        target_set = set(model_ids)
        for model_id, profile in self._models.items():
            profile.is_active = (model_id in target_set)

# Global singleton registry instance
model_registry = ModelRegistry()
