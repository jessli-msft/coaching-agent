"""Tests for the Governance Agent."""

from __future__ import annotations

import pytest

from src.agents.governance_agent import GovernanceAgent
from src.models.coaching import ComplianceStatus, GovernanceCheck


class TestGovernanceAgent:
    def test_returns_governance_check(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        assert isinstance(result, GovernanceCheck)

    def test_case_and_agent_ids_preserved(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        assert result.case_id == sample_case.case_id
        assert result.agent_id == sample_case.agent_id

    def test_compliance_items_non_empty(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        assert len(result.compliance_items) > 0

    def test_all_items_have_valid_status(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        valid_statuses = set(ComplianceStatus)
        for item in result.compliance_items:
            assert item.status in valid_statuses

    def test_overall_compliant_is_bool(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        assert isinstance(result.overall_compliant, bool)

    def test_critical_violations_are_listed_when_non_compliant(
        self, mock_settings, sample_case
    ):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        if not result.overall_compliant:
            assert len(result.critical_violations) > 0

    def test_failed_items_property(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        failed = result.failed_items
        for item in failed:
            assert item.status in (ComplianceStatus.FAIL, ComplianceStatus.WARNING)

    def test_summary_non_empty(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        assert result.summary.strip() != ""

    def test_failed_items_have_remediation_hints(self, mock_settings, sample_case):
        agent = GovernanceAgent(mock_settings)
        result = agent.check(sample_case)

        for item in result.failed_items:
            if item.status == ComplianceStatus.FAIL:
                assert item.remediation_hint.strip() != "", (
                    f"FAIL item {item.rule_id} should have a remediation hint"
                )
