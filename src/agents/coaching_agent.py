"""Coaching Agent.

Synthesises Quality Evaluation and Governance results into an actionable,
personalised CoachingSession for the service representative.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List

from src.config.settings import Settings
from src.models.case import Case
from src.models.coaching import (
    CoachingPriority,
    CoachingRecommendation,
    CoachingSession,
    GovernanceCheck,
)
from src.models.evaluation import QualityEvaluation

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Agent Coach embedded in Dynamics 365 Customer Service.
Your role is to produce actionable, empathetic, in-the-moment coaching for a customer
service representative based on quality evaluation scores and governance compliance results
for a recently resolved case.

Guidelines:
- Be specific — reference actual conversation moments where possible.
- Be constructive — frame feedback as growth opportunities, not criticism.
- Be concise — agents need to absorb feedback quickly between cases.
- Prioritise: address critical compliance failures first, then low quality scores.
- Provide concrete action_steps and, where helpful, an example_script.
- Keep opening and closing messages brief and motivational.

Respond ONLY with valid JSON matching this schema (no markdown, no explanations outside the JSON):
{
  "opening_message": "<2-3 sentence personalised opener>",
  "recommendations": [
    {
      "priority": "critical|high|medium|low",
      "title": "<short title>",
      "description": "<what happened and why it matters>",
      "action_steps": ["<step 1>", "<step 2>"],
      "related_dimension": "<dimension or rule>",
      "example_script": "<optional example phrasing>"
    }
  ],
  "closing_message": "<1-2 sentence motivational closer>"
}
"""

_MOCK_COACHING: Dict[str, Any] = {
    "opening_message": (
        "Great work resolving the customer's issue today, Alex! "
        "Your communication was clear and the customer left satisfied. "
        "Here are a few targeted tips to make your next interaction even stronger."
    ),
    "recommendations": [
        {
            "priority": "critical",
            "title": "Always Verify Customer Identity",
            "description": (
                "In this case, account data was accessed before the customer's identity "
                "was confirmed. This is a compliance requirement (RULE_001) and exposes "
                "both the customer and the company to data privacy risks."
            ),
            "action_steps": [
                "Before looking up any account, ask: 'For security purposes, could you please confirm your date of birth and the postcode on your account?'",
                "Log the verification outcome in the case notes.",
                "If the customer cannot verify, follow the unverified-customer escalation procedure.",
            ],
            "related_dimension": "RULE_001 - Identity Verification",
            "example_script": "Before we go ahead, I just need to verify a couple of details. Could you confirm your date of birth and the postcode associated with your account?",
        },
        {
            "priority": "medium",
            "title": "Acknowledge Recording Disclosure Verbally",
            "description": (
                "The automated greeting mentioned call recording, but it helps to "
                "verbally confirm this at the start of the conversation to ensure "
                "full transparency and satisfy RULE_003."
            ),
            "action_steps": [
                "After your greeting, add: 'Just to let you know, this call may be recorded for quality and training purposes.'",
            ],
            "related_dimension": "RULE_003 - Mandatory Disclosure",
            "example_script": "Just to let you know, this call may be recorded for quality and training purposes. Is that okay?",
        },
        {
            "priority": "medium",
            "title": "Deepen Empathy Responses",
            "description": (
                "Your empathy score was 7.5/10. You acknowledged the customer's frustration, "
                "which is great. To push to 9+, try mirroring the customer's emotion before "
                "moving to the solution."
            ),
            "action_steps": [
                "Pause after the customer describes their problem and name their emotion: 'I can hear how frustrating that must be.'",
                "Avoid jumping straight to the solution — take one extra turn to validate first.",
            ],
            "related_dimension": "empathy",
            "example_script": "I completely understand how frustrating that situation is — let me make sure we get this sorted for you right away.",
        },
        {
            "priority": "low",
            "title": "Reinforce Identity Verification as a Habit",
            "description": (
                "Process adherence scored 6.0/10 — the lowest across all dimensions. "
                "Beyond identity verification, review the full case-opening checklist "
                "to ensure no other steps are being missed."
            ),
            "action_steps": [
                "Review the case-opening procedure checklist in the knowledge base.",
                "Keep a printed copy of the checklist visible during calls until the steps feel automatic.",
            ],
            "related_dimension": "process_adherence",
            "example_script": None,
        },
    ],
    "closing_message": (
        "You're doing really well overall — keep building on those strengths! "
        "Focus on identity verification as your number-one priority this week."
    ),
}


class CoachingAgent:
    """Generates personalised coaching from QEA and Governance results."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AzureOpenAI  # type: ignore

            self._client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
            )
        return self._client

    def coach(
        self,
        case: Case,
        evaluation: QualityEvaluation,
        governance: GovernanceCheck,
    ) -> CoachingSession:
        """Produce a CoachingSession for the agent based on QEA + Governance results."""
        logger.info(
            "CoachingAgent: generating coaching for agent %s on case %s",
            case.agent_id,
            case.case_id,
        )

        if self.settings.mock_llm_responses:
            raw = _MOCK_COACHING
        else:
            raw = self._call_llm(case, evaluation, governance)

        return self._parse_response(raw, case, evaluation, governance)

    def _build_context(
        self,
        case: Case,
        evaluation: QualityEvaluation,
        governance: GovernanceCheck,
    ) -> str:
        """Build the user-facing context message sent to the LLM."""
        scores_text = "\n".join(
            f"  - {s.dimension.value}: {s.score}/10 — {s.justification}"
            for s in evaluation.scores
        )
        governance_text = "\n".join(
            f"  - [{item.status.value.upper()}] {item.rule_id} ({item.rule_name}): {item.finding}"
            for item in governance.compliance_items
        )

        return (
            f"Agent: {case.agent_name or case.agent_id}\n"
            f"Case ID: {case.case_id}\n"
            f"Category: {case.category}\n\n"
            f"QUALITY EVALUATION (Overall: {evaluation.overall_score}/10)\n"
            f"{scores_text}\n\n"
            f"Strengths: {', '.join(evaluation.strengths)}\n"
            f"Improvement Areas: {', '.join(evaluation.improvement_areas)}\n\n"
            f"GOVERNANCE RESULTS (Compliant: {governance.overall_compliant})\n"
            f"{governance_text}\n\n"
            f"Critical Violations: {', '.join(governance.critical_violations) or 'None'}\n\n"
            f"CONVERSATION TRANSCRIPT:\n{case.formatted_transcript}"
        )

    def _call_llm(
        self,
        case: Case,
        evaluation: QualityEvaluation,
        governance: GovernanceCheck,
    ) -> Dict[str, Any]:
        user_message = self._build_context(case, evaluation, governance)

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _parse_response(
        self,
        raw: Dict[str, Any],
        case: Case,
        evaluation: QualityEvaluation,
        governance: GovernanceCheck,
    ) -> CoachingSession:
        recommendations: List[CoachingRecommendation] = []
        for item in raw.get("recommendations", [])[: self.settings.max_coaching_recommendations]:
            try:
                priority = CoachingPriority(item["priority"])
            except ValueError:
                priority = CoachingPriority.MEDIUM

            recommendations.append(
                CoachingRecommendation(
                    priority=priority,
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    action_steps=item.get("action_steps", []),
                    related_dimension=item.get("related_dimension"),
                    example_script=item.get("example_script"),
                )
            )

        return CoachingSession(
            session_id=str(uuid.uuid4()),
            case_id=case.case_id,
            agent_id=case.agent_id,
            agent_name=case.agent_name,
            recommendations=recommendations,
            opening_message=raw.get("opening_message", ""),
            closing_message=raw.get("closing_message", ""),
            overall_quality_score=evaluation.overall_score,
            compliance_passed=governance.overall_compliant,
        )
