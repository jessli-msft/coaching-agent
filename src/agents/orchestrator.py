"""Agent Coach Orchestrator.

Coordinates the end-to-end workflow:
  Case  →  Quality Evaluation Agent  →  Governance Agent  →  Coaching Agent  →  CoachingSession
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from src.agents.coaching_agent import CoachingAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.quality_evaluation_agent import QualityEvaluationAgent
from src.config.settings import Settings
from src.models.case import Case
from src.models.coaching import CoachingSession, GovernanceCheck
from src.models.evaluation import QualityEvaluation

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationResult:
    """Holds the full outputs from one orchestration run."""

    case: Case
    evaluation: QualityEvaluation
    governance: GovernanceCheck
    coaching_session: CoachingSession


class AgentCoachOrchestrator:
    """Orchestrates QEA, Governance, and Coaching agents for a single case."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or Settings()
        self.qea = QualityEvaluationAgent(self.settings)
        self.governance_agent = GovernanceAgent(self.settings)
        self.coaching_agent = CoachingAgent(self.settings)

    def run(self, case: Case) -> OrchestrationResult:
        """Execute the full coaching pipeline for *case*."""
        logger.info("Orchestrator: starting pipeline for case %s", case.case_id)

        # Step 1 – Quality evaluation
        evaluation = self.qea.evaluate(case)
        logger.info(
            "Orchestrator: QEA complete — overall score %.1f",
            evaluation.overall_score,
        )

        # Step 2 – Governance check
        governance = self.governance_agent.check(case)
        logger.info(
            "Orchestrator: Governance complete — compliant=%s, critical=%s",
            governance.overall_compliant,
            governance.critical_violations,
        )

        # Step 3 – Generate coaching
        coaching_session = self.coaching_agent.coach(case, evaluation, governance)
        logger.info(
            "Orchestrator: Coaching generated — %d recommendations",
            len(coaching_session.recommendations),
        )

        return OrchestrationResult(
            case=case,
            evaluation=evaluation,
            governance=governance,
            coaching_session=coaching_session,
        )
