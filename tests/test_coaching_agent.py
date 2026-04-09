"""Tests for the Coaching Agent."""

from __future__ import annotations

import pytest

from src.agents.coaching_agent import CoachingAgent
from src.agents.governance_agent import GovernanceAgent
from src.agents.quality_evaluation_agent import QualityEvaluationAgent
from src.models.coaching import CoachingPriority, CoachingSession


class TestCoachingAgent:
    def _get_inputs(self, mock_settings, sample_case):
        """Helper: return (evaluation, governance) using mock agents."""
        evaluation = QualityEvaluationAgent(mock_settings).evaluate(sample_case)
        governance = GovernanceAgent(mock_settings).check(sample_case)
        return evaluation, governance

    def test_returns_coaching_session(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert isinstance(result, CoachingSession)

    def test_ids_and_names_preserved(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert result.case_id == sample_case.case_id
        assert result.agent_id == sample_case.agent_id
        assert result.agent_name == sample_case.agent_name

    def test_session_has_unique_id(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)

        session1 = agent.coach(sample_case, evaluation, governance)
        session2 = agent.coach(sample_case, evaluation, governance)

        assert session1.session_id != session2.session_id

    def test_recommendations_not_empty(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert len(result.recommendations) > 0

    def test_recommendations_capped_at_max(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert len(result.recommendations) <= mock_settings.max_coaching_recommendations

    def test_all_priorities_are_valid(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        valid_priorities = set(CoachingPriority)
        for rec in result.recommendations:
            assert rec.priority in valid_priorities

    def test_opening_and_closing_messages_non_empty(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert result.opening_message.strip() != ""
        assert result.closing_message.strip() != ""

    def test_quality_score_propagated(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert result.overall_quality_score == evaluation.overall_score

    def test_compliance_passed_propagated(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        assert result.compliance_passed == governance.overall_compliant

    def test_critical_recommendations_property(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        for rec in result.critical_recommendations:
            assert rec.priority == CoachingPriority.CRITICAL

    def test_each_recommendation_has_action_steps(self, mock_settings, sample_case):
        evaluation, governance = self._get_inputs(mock_settings, sample_case)
        agent = CoachingAgent(mock_settings)
        result = agent.coach(sample_case, evaluation, governance)

        for rec in result.recommendations:
            assert len(rec.action_steps) > 0, (
                f"Recommendation '{rec.title}' has no action steps"
            )
