"""Governance Agent.

Checks a customer service conversation against a configurable set of
compliance and governance rules, producing a GovernanceCheck report.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from src.config.settings import Settings
from src.models.case import Case
from src.models.coaching import ComplianceItem, ComplianceStatus, GovernanceCheck

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the Governance Agent for a Dynamics 365 Customer Service coaching
platform. Your role is to assess whether a customer service conversation complies with the
following governance rules:

RULE_001 - Identity Verification: Agent must verify customer identity before accessing account data.
RULE_002 - Data Privacy: Agent must not share PII with unverified third parties.
RULE_003 - Mandatory Disclosure: Agent must inform the customer when the call is being recorded.
RULE_004 - Escalation Protocol: Agent must offer escalation if the issue remains unresolved after two attempts.
RULE_005 - Closing Procedure: Agent must summarise next steps and confirm customer satisfaction before closing.
RULE_006 - Prohibited Language: Agent must not use dismissive, rude, or discriminatory language.
RULE_007 - Accurate Promises: Agent must not make promises outside their authorisation level.

Respond ONLY with valid JSON matching this schema (no markdown, no explanations outside the JSON):
{
  "compliance_items": [
    {
      "rule_id": "RULE_XXX",
      "rule_name": "<name>",
      "status": "pass|fail|warning|not_applicable",
      "description": "<what this rule checks>",
      "finding": "<what you found in the transcript>",
      "remediation_hint": "<how to fix, empty string if pass/not_applicable>"
    }
  ],
  "overall_compliant": true|false,
  "critical_violations": ["RULE_XXX"],
  "summary": "<2-3 sentence narrative>"
}
"""

_MOCK_GOVERNANCE: Dict[str, Any] = {
    "compliance_items": [
        {
            "rule_id": "RULE_001",
            "rule_name": "Identity Verification",
            "status": "fail",
            "description": "Agent must verify customer identity before accessing account data.",
            "finding": "No identity verification question was asked before the agent accessed the account.",
            "remediation_hint": "Always ask for at least two identifying factors (e.g., date of birth + postcode) before pulling up account details.",
        },
        {
            "rule_id": "RULE_002",
            "rule_name": "Data Privacy",
            "status": "pass",
            "description": "Agent must not share PII with unverified third parties.",
            "finding": "No PII shared with third parties.",
            "remediation_hint": "",
        },
        {
            "rule_id": "RULE_003",
            "rule_name": "Mandatory Disclosure",
            "status": "warning",
            "description": "Agent must inform the customer when the call is being recorded.",
            "finding": "Recording disclosure was present in the automated greeting but not acknowledged by the agent.",
            "remediation_hint": "Verbally confirm the recording disclosure at the start of the conversation.",
        },
        {
            "rule_id": "RULE_004",
            "rule_name": "Escalation Protocol",
            "status": "not_applicable",
            "description": "Agent must offer escalation if issue remains unresolved after two attempts.",
            "finding": "Issue was resolved on first attempt.",
            "remediation_hint": "",
        },
        {
            "rule_id": "RULE_005",
            "rule_name": "Closing Procedure",
            "status": "pass",
            "description": "Agent must summarise next steps and confirm customer satisfaction before closing.",
            "finding": "Agent summarised the resolution and confirmed customer was satisfied.",
            "remediation_hint": "",
        },
        {
            "rule_id": "RULE_006",
            "rule_name": "Prohibited Language",
            "status": "pass",
            "description": "Agent must not use dismissive, rude, or discriminatory language.",
            "finding": "No prohibited language detected.",
            "remediation_hint": "",
        },
        {
            "rule_id": "RULE_007",
            "rule_name": "Accurate Promises",
            "status": "pass",
            "description": "Agent must not make promises outside their authorisation level.",
            "finding": "All commitments made were within authorisation scope.",
            "remediation_hint": "",
        },
    ],
    "overall_compliant": False,
    "critical_violations": ["RULE_001"],
    "summary": (
        "The conversation has one critical compliance failure: identity verification was skipped. "
        "There is also a minor warning regarding the recording disclosure. "
        "All other governance rules were satisfied."
    ),
}


class GovernanceAgent:
    """Checks conversation governance / compliance for a given Case."""

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

    def check(self, case: Case) -> GovernanceCheck:
        """Run governance checks on *case* and return a GovernanceCheck."""
        logger.info(
            "GovernanceAgent: checking case %s for agent %s",
            case.case_id,
            case.agent_id,
        )

        if self.settings.mock_llm_responses:
            raw = _MOCK_GOVERNANCE
        else:
            raw = self._call_llm(case)

        return self._parse_response(raw, case)

    def _call_llm(self, case: Case) -> Dict[str, Any]:
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

    def _parse_response(self, raw: Dict[str, Any], case: Case) -> GovernanceCheck:
        items: List[ComplianceItem] = []
        for item in raw.get("compliance_items", []):
            try:
                status = ComplianceStatus(item["status"])
            except ValueError:
                status = ComplianceStatus.NOT_APPLICABLE

            items.append(
                ComplianceItem(
                    rule_id=item.get("rule_id", ""),
                    rule_name=item.get("rule_name", ""),
                    status=status,
                    description=item.get("description", ""),
                    finding=item.get("finding", ""),
                    remediation_hint=item.get("remediation_hint", ""),
                )
            )

        return GovernanceCheck(
            case_id=case.case_id,
            agent_id=case.agent_id,
            compliance_items=items,
            overall_compliant=bool(raw.get("overall_compliant", True)),
            critical_violations=raw.get("critical_violations", []),
            summary=raw.get("summary", ""),
        )
