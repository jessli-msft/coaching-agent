"""Tests for the Quality Evaluation Agent."""

from __future__ import annotations

import pytest

from src.agents.quality_evaluation_agent import QualityEvaluationAgent
from src.models.evaluation import QualityDimension, QualityEvaluation


class TestQualityEvaluationAgent:
    def test_returns_quality_evaluation(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        assert isinstance(result, QualityEvaluation)

    def test_case_and_agent_ids_preserved(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        assert result.case_id == sample_case.case_id
        assert result.agent_id == sample_case.agent_id

    def test_scores_within_range(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        for score in result.scores:
            assert 0.0 <= score.score <= 10.0, f"Score out of range for {score.dimension}"

    def test_overall_score_within_range(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        assert 0.0 <= result.overall_score <= 10.0

    def test_all_quality_dimensions_present(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        dimensions_returned = {s.dimension for s in result.scores}
        for dim in QualityDimension:
            assert dim in dimensions_returned, f"Missing dimension: {dim}"

    def test_strengths_and_improvement_areas_non_empty(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        assert len(result.strengths) > 0
        assert len(result.improvement_areas) > 0

    def test_summary_non_empty(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        assert result.summary.strip() != ""

    def test_score_by_dimension_accessor(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        empathy_score = result.score_by_dimension(QualityDimension.EMPATHY)
        assert empathy_score is not None
        assert 0.0 <= empathy_score <= 10.0

    def test_scores_as_dict(self, mock_settings, sample_case):
        agent = QualityEvaluationAgent(mock_settings)
        result = agent.evaluate(sample_case)

        d = result.scores_as_dict()
        assert isinstance(d, dict)
        assert QualityDimension.EMPATHY.value in d
