# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for health check scoring and pattern memory -- Batch 15.

Covers: workflows/health_check_scoring, meta_workflows/pattern_memory.

(Formerly also covered workflow_morning/workflow_learn -- removed with
the legacy one-command family; see
docs/reports/d-block-triage-2026-07-14.md.)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# === Module: workflows/health_check_scoring.py ===


class TestHealthCheckScoring:
    def test_category_weights_sum_to_one(self):
        from attune.workflows.health_check_scoring import CATEGORY_WEIGHTS

        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_grade_thresholds_exist(self):
        from attune.workflows.health_check_scoring import GRADE_THRESHOLDS

        for grade in ("A", "B", "C", "D"):
            assert grade in GRADE_THRESHOLDS

    def test_assign_grade_a(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(95.0) == "A"

    def test_assign_grade_b(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(85.0) == "B"

    def test_assign_grade_c(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(75.0) == "C"

    def test_assign_grade_d(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(65.0) == "D"

    def test_assign_grade_f(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(55.0) == "F"

    def test_assign_grade_custom_thresholds(self):
        from attune.workflows.health_check_scoring import assign_grade

        assert assign_grade(50.0, thresholds={"A": 40.0}) == "A"

    def test_calculate_overall_score_weighted(self):
        from attune.workflows.health_check_scoring import calculate_overall_score

        mock_score = MagicMock()
        mock_score.score = 80.0
        mock_score.weight = 1.0

        result = calculate_overall_score([mock_score])
        assert result == 80.0

    def test_calculate_overall_score_empty(self):
        from attune.workflows.health_check_scoring import calculate_overall_score

        assert calculate_overall_score([]) == 0.0

    def test_calculate_overall_score_multiple(self):
        from attune.workflows.health_check_scoring import calculate_overall_score

        a = MagicMock(score=100.0, weight=0.5)
        b = MagicMock(score=60.0, weight=0.5)
        result = calculate_overall_score([a, b])
        assert abs(result - 80.0) < 1e-9

    def test_calculate_category_scores_security(self):
        from attune.workflows.health_check_scoring import calculate_category_scores

        agent_results = {
            "security_auditor": {
                "output": {"critical_issues": 0, "high_issues": 0, "medium_issues": 0}
            },
            "test_coverage_analyzer": {"output": {"coverage_percent": 90.0}},
            "code_reviewer": {"output": {"quality_score": 8.0}},
        }
        scores = calculate_category_scores(agent_results)
        names = [s.name for s in scores]
        assert "Security" in names
        assert "Coverage" in names
        assert "Quality" in names

    def test_calculate_category_scores_security_deductions(self):
        from attune.workflows.health_check_scoring import calculate_category_scores

        agent_results = {
            "security_auditor": {
                "output": {"critical_issues": 2, "high_issues": 1, "medium_issues": 0}
            },
            "test_coverage_analyzer": {"output": {"coverage_percent": 80.0}},
            "code_reviewer": {"output": {"quality_score": 7.0}},
        }
        scores = calculate_category_scores(agent_results)
        security = next(s for s in scores if s.name == "Security")
        # 2 critical * 20 + 1 high * 10 = 50 deducted -> score = 50
        assert security.score == 50.0

    def test_calculate_category_scores_with_performance(self):
        from attune.workflows.health_check_scoring import calculate_category_scores

        agent_results = {
            "security_auditor": {"output": {}},
            "test_coverage_analyzer": {"output": {"coverage_percent": 85.0}},
            "code_reviewer": {"output": {"quality_score": 7.5}},
            "performance_optimizer": {"output": {"bottleneck_count": 2}},
        }
        scores = calculate_category_scores(agent_results)
        names = [s.name for s in scores]
        assert "Performance" in names

    def test_generate_recommendations_healthy(self):
        from attune.workflows.health_check_scoring import generate_recommendations

        mock_score = MagicMock(passed=True, score=95.0, name="Security")
        recs = generate_recommendations([mock_score])
        assert any("good" in r.lower() or "✅" in r for r in recs)

    def test_generate_recommendations_failing(self):
        from attune.workflows.health_check_scoring import generate_recommendations

        mock_score = MagicMock()
        mock_score.passed = False
        mock_score.name = "Coverage"
        mock_score.score = 60.0
        mock_score.issues = ["Coverage below 80%"]
        mock_score.raw_metrics = {"coverage_percent": 60.0}

        recs = generate_recommendations([mock_score])
        assert len(recs) > 0
        assert any("coverage" in r.lower() or "Coverage" in r for r in recs)

    def test_generate_recommendations_tip_on_many_issues(self):
        from attune.workflows.health_check_scoring import generate_recommendations

        def _failing(name):
            m = MagicMock()
            m.passed = False
            m.name = name
            m.score = 30.0
            m.issues = ["issue"]
            m.raw_metrics = {"quality_score": 3.0, "bottleneck_count": 5}
            return m

        scores = [_failing("Security"), _failing("Coverage"), _failing("Quality")]
        recs = generate_recommendations(scores)
        assert any("Tip" in r or "priority" in r.lower() for r in recs)


# === Module: meta_workflows/pattern_memory.py ===


class TestPatternMemoryMixin:
    def _make_mixin_instance(self, has_memory=True):
        from attune.meta_workflows.pattern_memory import PatternMemoryMixin

        class ConcreteClass(PatternMemoryMixin):
            def __init__(self):
                self.memory = MagicMock() if has_memory else None
                self.executions_dir = MagicMock()

            def get_recommendations(self, template_id, min_confidence=0.7):
                return [f"rec for {template_id}"]

        return ConcreteClass()

    def test_store_execution_no_memory_returns_none(self):
        instance = self._make_mixin_instance(has_memory=False)
        mock_result = MagicMock()
        result = instance.store_execution_in_memory(mock_result)
        assert result is None

    def test_store_execution_with_memory(self):
        instance = self._make_mixin_instance(has_memory=True)

        mock_result = MagicMock()
        mock_result.run_id = "run-001"
        mock_result.template_id = "health-check"
        mock_result.success = True
        mock_result.total_cost = 0.5
        mock_result.total_duration = 10.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses.responses = {}
        mock_result.timestamp = "2026-01-01"
        mock_result.error = None

        instance.memory.persist_pattern.return_value = {"pattern_id": "pat-001"}

        result = instance.store_execution_in_memory(mock_result)
        assert result == "pat-001"

    def test_store_execution_handles_exception(self):
        instance = self._make_mixin_instance(has_memory=True)
        instance.memory.persist_pattern.side_effect = RuntimeError("DB error")

        mock_result = MagicMock()
        mock_result.run_id = "run-002"
        mock_result.template_id = "t"
        mock_result.success = True
        mock_result.total_cost = 0.1
        mock_result.total_duration = 1.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses.responses = {}
        mock_result.timestamp = "2026-01-01"
        mock_result.error = None

        result = instance.store_execution_in_memory(mock_result)
        assert result is None

    def test_search_executions_no_memory_falls_back(self):
        instance = self._make_mixin_instance(has_memory=False)

        with patch("attune.meta_workflows.pattern_memory.list_execution_results", return_value=[]):
            results = instance.search_executions_by_context("query")
        assert results == []

    def test_search_executions_with_memory(self):
        instance = self._make_mixin_instance(has_memory=True)

        instance.memory.search_patterns.return_value = []

        results = instance.search_executions_by_context("successful security audits")
        assert results == []

    def test_get_smart_recommendations_no_memory(self):
        instance = self._make_mixin_instance(has_memory=False)
        recs = instance.get_smart_recommendations("health-check")
        assert "rec for health-check" in recs

    def test_get_smart_recommendations_with_memory(self):
        instance = self._make_mixin_instance(has_memory=True)
        instance.memory.search_patterns.return_value = []

        recs = instance.get_smart_recommendations("health-check", form_response=None)
        assert "rec for health-check" in recs
