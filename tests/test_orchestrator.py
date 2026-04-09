"""Integration test for the full orchestration pipeline."""

from __future__ import annotations

import pytest

from src.agents.orchestrator import AgentCoachOrchestrator, OrchestrationResult
from src.models.coaching import CoachingPriority


class TestAgentCoachOrchestrator:
    def test_full_pipeline_returns_result(self, mock_settings, sample_case):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        assert isinstance(result, OrchestrationResult)

    def test_all_fields_populated(self, mock_settings, sample_case):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        assert result.case is sample_case
        assert result.evaluation is not None
        assert result.governance is not None
        assert result.coaching_session is not None

    def test_case_ids_consistent_across_pipeline(self, mock_settings, sample_case):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        assert result.evaluation.case_id == sample_case.case_id
        assert result.governance.case_id == sample_case.case_id
        assert result.coaching_session.case_id == sample_case.case_id

    def test_agent_ids_consistent_across_pipeline(self, mock_settings, sample_case):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        assert result.evaluation.agent_id == sample_case.agent_id
        assert result.governance.agent_id == sample_case.agent_id
        assert result.coaching_session.agent_id == sample_case.agent_id

    def test_coaching_session_has_recommendations(self, mock_settings, sample_case):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        assert len(result.coaching_session.recommendations) > 0

    def test_compliance_failure_produces_critical_recommendation(
        self, mock_settings, sample_case
    ):
        orchestrator = AgentCoachOrchestrator(mock_settings)
        result = orchestrator.run(sample_case)

        # The mock governance result has a critical violation, so we expect
        # at least one CRITICAL coaching recommendation.
        if not result.governance.overall_compliant:
            priorities = {r.priority for r in result.coaching_session.recommendations}
            assert CoachingPriority.CRITICAL in priorities, (
                "Expected a CRITICAL recommendation when governance check fails"
            )
