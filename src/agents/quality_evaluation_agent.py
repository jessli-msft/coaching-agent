"""Quality Evaluation Agent (QEA).

Evaluates a customer service conversation across multiple quality dimensions
and produces a structured QualityEvaluation report.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List

from src.config.settings import Settings
from src.models.case import Case
from src.models.evaluation import (
    EvaluationScore,
    QualityDimension,
    QualityEvaluation,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Quality Evaluation Agent (QEA) for a Dynamics 365 Customer Service
coaching platform. Your job is to rigorously evaluate a customer service conversation transcript
across the following quality dimensions:

- empathy: Did the agent acknowledge customer emotions and show understanding?
- resolution_effectiveness: Was the customer's issue actually resolved or meaningfully progressed?
- communication_clarity: Was the agent's language clear, professional and free of jargon?
- process_adherence: Did the agent follow standard procedures (greeting, verification, wrap-up, etc.)?
- customer_effort: Did the agent minimise the effort required from the customer?
- knowledge_accuracy: Were the agent's statements factually correct and appropriately detailed?

Respond ONLY with valid JSON matching this schema (no markdown, no explanations outside the JSON):
{
  "scores": [
    {
      "dimension": "<dimension_name>",
      "score": <float 0-10>,
      "justification": "<one-sentence reason>",
      "evidence": ["<transcript excerpt>"]
    }
  ],
  "overall_score": <float 0-10>,
  "strengths": ["<strength>"],
  "improvement_areas": ["<area>"],
  "summary": "<2-3 sentence narrative>"
}
"""

_MOCK_EVALUATION: Dict[str, Any] = {
    "scores": [
        {
            "dimension": "empathy",
            "score": 7.5,
            "justification": "Agent acknowledged frustration but could have been warmer.",
            "evidence": ["I understand that's frustrating"],
        },
        {
            "dimension": "resolution_effectiveness",
            "score": 8.0,
            "justification": "Issue was resolved by end of conversation.",
            "evidence": ["Your account has been updated"],
        },
        {
            "dimension": "communication_clarity",
            "score": 8.5,
            "justification": "Clear, professional language throughout.",
            "evidence": [],
        },
        {
            "dimension": "process_adherence",
            "score": 6.0,
            "justification": "Agent skipped identity verification step.",
            "evidence": ["[No verification question asked]"],
        },
        {
            "dimension": "customer_effort",
            "score": 7.0,
            "justification": "Customer had to repeat themselves once.",
            "evidence": [],
        },
        {
            "dimension": "knowledge_accuracy",
            "score": 9.0,
            "justification": "All information provided was accurate.",
            "evidence": [],
        },
    ],
    "overall_score": 7.7,
    "strengths": ["Clear communication", "Effective resolution"],
    "improvement_areas": ["Identity verification", "Empathy language"],
    "summary": (
        "The agent resolved the issue effectively and communicated clearly. "
        "Key improvement areas are strengthening empathy language and consistently "
        "following the identity verification process."
    ),
}


class QualityEvaluationAgent:
    """Evaluates conversation quality for a given Case."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None

    def _get_client(self):
        """Lazily create the Azure OpenAI client."""
        if self._client is None:
            from openai import AzureOpenAI  # type: ignore

            self._client = AzureOpenAI(
                azure_endpoint=self.settings.azure_openai_endpoint,
                api_key=self.settings.azure_openai_api_key,
                api_version=self.settings.azure_openai_api_version,
            )
        return self._client

    def evaluate(self, case: Case) -> QualityEvaluation:
        """Run quality evaluation on *case* and return a QualityEvaluation."""
        logger.info("QEA: evaluating case %s for agent %s", case.case_id, case.agent_id)

        if self.settings.mock_llm_responses:
            raw = _MOCK_EVALUATION
        else:
            raw = self._call_llm(case)

        return self._parse_response(raw, case)

    def _call_llm(self, case: Case) -> Dict[str, Any]:
        """Send the transcript to Azure OpenAI and parse the JSON response."""
        user_message = (
            f"Case ID: {case.case_id}\n"
            f"Category: {case.category}\n\n"
            f"Transcript:\n{case.formatted_transcript}"
        )

        client = self._get_client()
        response = client.chat.completions.create(
            model=self.settings.azure_openai_deployment_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def _parse_response(self, raw: Dict[str, Any], case: Case) -> QualityEvaluation:
        scores: List[EvaluationScore] = []
        for item in raw.get("scores", []):
            try:
                dimension = QualityDimension(item["dimension"])
            except ValueError:
                logger.warning("Unknown dimension '%s', skipping.", item.get("dimension"))
                continue
            scores.append(
                EvaluationScore(
                    dimension=dimension,
                    score=float(item.get("score", 0)),
                    justification=item.get("justification", ""),
                    evidence=item.get("evidence", []),
                )
            )

        return QualityEvaluation(
            case_id=case.case_id,
            agent_id=case.agent_id,
            scores=scores,
            overall_score=float(raw.get("overall_score", 0.0)),
            strengths=raw.get("strengths", []),
            improvement_areas=raw.get("improvement_areas", []),
            summary=raw.get("summary", ""),
        )
