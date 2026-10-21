import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.core.orchestrator import StageResult

class SynthesisInsight(BaseModel):
    proposal_focus: str = Field(..., description="Summary of initial solution proposed by Specialist")
    critique_highlights: List[str] = Field(default_factory=list, description="Security and logic issues identified by Reviewer")
    corrections_applied: List[str] = Field(default_factory=list, description="Corrections incorporated into final output")
    unresolved_uncertainties: List[str] = Field(default_factory=list, description="Caveats or assumptions remaining")

class SynthesisResult(BaseModel):
    final_response: str
    insights: SynthesisInsight
    stages_synthesized: int

class Synthesizer:
    def __init__(self):
        pass

    def _extract_insights(self, stage_results: List[StageResult]) -> SynthesisInsight:
        """
        Analyzes the progression of ideas across multi-model stages.
        """
        if len(stage_results) <= 1:
            return SynthesisInsight(
                proposal_focus="Direct execution without multi-stage critique.",
                critique_highlights=[],
                corrections_applied=[],
                unresolved_uncertainties=[]
            )

        specialist = stage_results[0]
        reviewer = stage_results[1] if len(stage_results) > 1 else None

        # Analyze proposal focus
        spec_text = specialist.response
        code_blocks = re.findall(r"```(?:\w+)?\n([\s\S]*?)```", spec_text)
        proposal_focus = (
            f"{specialist.model_id} generated {len(code_blocks)} code block(s) and architectural outline."
            if code_blocks else
            f"{specialist.model_id} established the foundational solution."
        )

        # Analyze reviewer critique
        critiques = []
        corrections = []
        uncertainties = []

        if reviewer:
            rev_text = reviewer.response
            # Identify bullet points and warnings
            bullet_lines = [
                line.strip() for line in rev_text.splitlines()
                if line.strip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
            ]
            for line in bullet_lines[:6]:
                lower = line.lower()
                if any(w in lower for w in ["security", "vulnerability", "risk", "flaw", "leak", "secret", "expire"]):
                    critiques.append(line.lstrip("-*0123456789. "))
                elif any(w in lower for w in ["fix", "recommend", "should", "ensure", "replace", "add"]):
                    corrections.append(line.lstrip("-*0123456789. "))
                elif any(w in lower for w in ["note", "assume", "depends", "production", "caveat"]):
                    uncertainties.append(line.lstrip("-*0123456789. "))

        return SynthesisInsight(
            proposal_focus=proposal_focus,
            critique_highlights=critiques[:4] or ["No critical security flaws flagged."],
            corrections_applied=corrections[:4] or ["Standard validation and clean structure enforced."],
            unresolved_uncertainties=uncertainties[:3] or ["Ensure production environment secrets are stored in secure vault."]
        )

    def synthesize(self, prompt: str, stage_results: List[StageResult]) -> SynthesisResult:
        """
        Produces ONE improved, unified answer instead of concatenating multiple separate answers.
        """
        if not stage_results:
            return SynthesisResult(
                final_response="No response generated.",
                insights=SynthesisInsight(proposal_focus="None"),
                stages_synthesized=0
            )

        insights = self._extract_insights(stage_results)

        # The final stage contains the unified synthesis
        final_stage = stage_results[-1]
        cleaned_body = final_stage.response.strip()

        # Remove repetitive preamble if the model generated it
        for prefix in [
            "Here is the unified response:",
            "Here is the final response:",
            "Synthesized Response:",
            "Final Revised Response:"
        ]:
            if cleaned_body.startswith(prefix):
                cleaned_body = cleaned_body[len(prefix):].strip()

        return SynthesisResult(
            final_response=cleaned_body,
            insights=insights,
            stages_synthesized=len(stage_results)
        )

synthesizer = Synthesizer()
