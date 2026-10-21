from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.core.orchestrator import StageResult

class EvaluationMetric(BaseModel):
    status: str = Field(..., description="Qualitative evaluation state: Single Model Response, Multi-Model Review, Simulation — Not Evaluated, or Not Verified")
    execution_type: str = Field(default="real", description="real or simulated")
    model_agreement: Optional[bool] = None
    notes: List[str] = Field(default_factory=list)
    disagreements_found: List[str] = Field(default_factory=list)
    # Numerical consensus percentage removed per v0.4.1 specification
    consistency_score: Optional[float] = None

class Evaluator:
    def evaluate(self, stage_results: List[StageResult], simulated: bool = False) -> EvaluationMetric:
        """
        Evaluates agreement across multi-model stages without arbitrary numerical percentages.
        Distinguishes:
        - Single Model Response
        - Multi-Model Review
        - Simulation — Not Evaluated
        - Not Verified
        """
        if not stage_results:
            return EvaluationMetric(
                status="Not Verified",
                execution_type="simulated" if simulated else "real",
                model_agreement=None,
                notes=["No stage results available for verification."],
                disagreements_found=[]
            )

        # Check if any stage was simulated or if simulated mode is active
        has_simulated = simulated or any(s.status in ("simulated", "fallback_simulated") for s in stage_results)
        if has_simulated:
            return EvaluationMetric(
                status="Simulation — Not Evaluated",
                execution_type="simulated",
                model_agreement=None,
                notes=["Simulated execution: consensus evaluation disabled."],
                disagreements_found=[]
            )

        unique_models = set(s.model_id for s in stage_results)

        if len(stage_results) <= 1 or len(unique_models) <= 1:
            return EvaluationMetric(
                status="Single Model Response",
                execution_type="real",
                model_agreement=True,
                notes=[f"Direct response from single model ({stage_results[0].model_id})."],
                disagreements_found=[]
            )

        # Multiple real models
        notes = []
        disagreements = []

        reviewer_stages = [s for s in stage_results if "review" in s.role.lower() or "review" in s.stage_name.lower()]
        has_criticisms = False

        for r in reviewer_stages:
            resp_lower = r.response.lower()
            warning_cues = ["vulnerability", "bug", "flaw", "incorrect", "caution", "issue", "security risk"]
            found_cues = [cue for cue in warning_cues if cue in resp_lower]
            if found_cues:
                has_criticisms = True
                disagreements.append(f"{r.model_id} flagged: {', '.join(found_cues)}")

        if has_criticisms:
            notes.append("Peer reviewer highlighted edge cases and security points for synthesis integration.")
        else:
            notes.append("Peer models aligned on core implementation and approach.")

        return EvaluationMetric(
            status="Multi-Model Review",
            execution_type="real",
            model_agreement=not has_criticisms,
            notes=notes,
            disagreements_found=disagreements
        )

evaluator = Evaluator()
