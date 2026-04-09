"""Data models for quality evaluation results produced by the QEA."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class QualityDimension(str, Enum):
    """The evaluation dimensions assessed by the Quality Evaluation Agent."""

    EMPATHY = "empathy"
    RESOLUTION_EFFECTIVENESS = "resolution_effectiveness"
    COMMUNICATION_CLARITY = "communication_clarity"
    PROCESS_ADHERENCE = "process_adherence"
    CUSTOMER_EFFORT = "customer_effort"
    KNOWLEDGE_ACCURACY = "knowledge_accuracy"


class EvaluationScore(BaseModel):
    """Score and justification for a single quality dimension."""

    dimension: QualityDimension
    score: float = Field(..., ge=0.0, le=10.0, description="Score from 0 to 10")
    justification: str = Field(
        default="", description="LLM explanation for the assigned score"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Specific conversation excerpts supporting the score",
    )


class QualityEvaluation(BaseModel):
    """Full quality evaluation result for a single case."""

    case_id: str
    agent_id: str
    scores: List[EvaluationScore] = Field(default_factory=list)
    overall_score: float = Field(
        default=0.0, ge=0.0, le=10.0, description="Weighted overall score"
    )
    strengths: List[str] = Field(
        default_factory=list, description="Observed agent strengths"
    )
    improvement_areas: List[str] = Field(
        default_factory=list,
        description="Areas where the agent could improve",
    )
    summary: str = Field(default="", description="Narrative summary of the evaluation")

    def score_by_dimension(self, dimension: QualityDimension) -> Optional[float]:
        """Convenience accessor – returns the score for a specific dimension."""
        for s in self.scores:
            if s.dimension == dimension:
                return s.score
        return None

    def scores_as_dict(self) -> Dict[str, float]:
        return {s.dimension.value: s.score for s in self.scores}
