# Licensed under the Apache License, Version 2.0
# Copyright 2025 Smart AI Memory, LLC
"""Tests for health check scoring, pattern memory, workflow_morning,
and workflow_learn — Batch 15.

Covers: workflows/health_check_scoring, meta_workflows/pattern_memory,
workflow_morning, workflow_learn.
"""

from __future__ import annotations

import sys
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


# === Module: workflow_morning.py ===


class TestWorkflowMorning:
    def _make_wc(self):
        mock_wc = MagicMock()
        mock_wc._load_stats.return_value = {"commands": {}, "last_session": ""}
        mock_wc._load_patterns.return_value = {"debugging": [], "security": [], "inspection": []}
        mock_wc._get_tech_debt_trend.return_value = "stable"
        mock_wc._run_command.return_value = (True, "")
        mock_wc._save_stats.return_value = None
        return mock_wc

    def test_morning_workflow_returns_zero(self):
        from attune.workflow_morning import morning_workflow

        mock_wc = self._make_wc()
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = morning_workflow()
        assert result == 0

    def test_morning_workflow_updates_stats(self):
        from attune.workflow_morning import morning_workflow

        mock_wc = self._make_wc()
        stats = {"commands": {}, "last_session": ""}
        mock_wc._load_stats.return_value = stats

        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            morning_workflow()
        assert stats["commands"].get("morning", 0) == 1

    def test_morning_workflow_prints_header(self, capsys):
        from attune.workflow_morning import morning_workflow

        mock_wc = self._make_wc()
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            morning_workflow()
        out = capsys.readouterr().out
        assert "MORNING BRIEFING" in out

    def test_print_patterns_section_returns_count(self, capsys):
        from attune.workflow_morning import _print_patterns_section

        patterns = {
            "debugging": [{"status": "resolved"}, {"status": "investigating"}],
            "security": [{}],
            "inspection": [],
        }
        count = _print_patterns_section(patterns)
        assert count == 2
        out = capsys.readouterr().out
        assert "Bug patterns" in out

    def test_print_patterns_section_recent_bugs(self, capsys):
        from datetime import datetime, timezone

        from attune.workflow_morning import _print_patterns_section

        recent_ts = datetime.now(tz=timezone.utc).isoformat()
        patterns = {
            "debugging": [
                {
                    "status": "resolved",
                    "timestamp": recent_ts,
                    "bug_type": "null_reference",
                    "root_cause": "missing check",
                }
            ],
            "security": [],
            "inspection": [],
        }
        _print_patterns_section(patterns)
        out = capsys.readouterr().out
        assert "New this week" in out

    def test_print_tech_debt_section_stable(self, capsys):
        from attune.workflow_morning import _print_tech_debt_section

        mock_wc = MagicMock()
        mock_wc._get_tech_debt_trend.return_value = "stable"

        trend = _print_tech_debt_section(mock_wc, "./patterns")
        out = capsys.readouterr().out
        assert trend == "stable"
        assert "Stable" in out

    def test_print_health_check_ok(self, capsys):
        from attune.workflow_morning import _print_health_check

        mock_wc = MagicMock()
        mock_wc._run_command.return_value = (True, "")

        _print_health_check(mock_wc, ".")
        out = capsys.readouterr().out
        assert "QUICK HEALTH CHECK" in out

    def test_cmd_morning_delegates(self):
        from attune.workflow_morning import cmd_morning

        mock_wc = MagicMock()
        mock_wc.morning_workflow.return_value = 0
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            args = MagicMock()
            args.patterns_dir = "./patterns"
            args.project_root = "."
            args.verbose = False
            result = cmd_morning(args)
        assert result == 0
        mock_wc.morning_workflow.assert_called_once()

    def test_wc_late_binding(self):
        from attune.workflow_morning import _wc

        mock_wc = MagicMock()
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = _wc()
        assert result is mock_wc

    def test_trend_messages_all_keys(self):
        from attune.workflow_morning import _TREND_MESSAGES

        for key in ("increasing", "decreasing", "stable", "unknown", "insufficient_data"):
            assert key in _TREND_MESSAGES


# === Module: workflow_learn.py ===


class TestWorkflowLearn:
    def _make_wc(self):
        mock_wc = MagicMock()
        mock_wc._run_command.return_value = (True, "")
        mock_wc._load_stats.return_value = {"commands": {}, "patterns_learned": 0}
        mock_wc._save_stats.return_value = None
        return mock_wc

    def test_classify_bug_type_null_reference(self):
        from attune.workflow_learn import _classify_bug_type

        assert _classify_bug_type("fix null pointer exception") == "null_reference"

    def test_classify_bug_type_async(self):
        from attune.workflow_learn import _classify_bug_type

        assert _classify_bug_type("fix async timeout") == "async_timing"

    def test_classify_bug_type_import(self):
        from attune.workflow_learn import _classify_bug_type

        assert _classify_bug_type("fix import error") == "import_error"

    def test_classify_bug_type_type_mismatch(self):
        from attune.workflow_learn import _classify_bug_type

        assert _classify_bug_type("fix type cast issue") == "type_mismatch"

    def test_classify_bug_type_unknown(self):
        from attune.workflow_learn import _classify_bug_type

        assert _classify_bug_type("add a new feature") == "unknown"

    def test_extract_bug_pattern_non_fix_returns_none(self):
        from attune.workflow_learn import _extract_bug_pattern

        parts = ["abc1234def", "refactor code", "author", "2026-01-01"]
        mock_wc = MagicMock()
        result = _extract_bug_pattern(parts, mock_wc, verbose=False)
        assert result is None

    def test_extract_bug_pattern_fix_returns_dict(self):
        from attune.workflow_learn import _extract_bug_pattern

        parts = ["abc1234def5678", "fix null pointer bug", "John Doe", "2026-01-01T00:00:00"]
        mock_wc = MagicMock()
        mock_wc._run_command.return_value = (True, "src/utils.py | 10 +++---")
        result = _extract_bug_pattern(parts, mock_wc, verbose=False)
        assert result is not None
        assert result["bug_type"] == "null_reference"
        assert result["status"] == "resolved"

    def test_learn_workflow_no_git_returns_one(self):
        from attune.workflow_learn import learn_workflow

        mock_wc = self._make_wc()
        mock_wc._run_command.return_value = (False, "not a git repo")
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = learn_workflow()
        assert result == 1

    def test_learn_workflow_success(self, tmp_path):
        from attune.workflow_learn import learn_workflow

        mock_wc = self._make_wc()
        # Empty git log — no commits to analyze
        mock_wc._run_command.return_value = (True, "")

        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = learn_workflow(patterns_dir=str(tmp_path / "patterns"))
        assert result == 0

    def test_learn_workflow_extracts_patterns(self, tmp_path):
        from attune.workflow_learn import learn_workflow

        mock_wc = self._make_wc()

        def run_command_side_effect(cmd):
            if "git" in cmd and "log" in cmd:
                return (True, "abc1234def5678|fix null pointer|dev|2026-01-01T00:00:00")
            return (True, "")

        mock_wc._run_command.side_effect = run_command_side_effect

        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = learn_workflow(patterns_dir=str(tmp_path / "patterns"))
        assert result == 0

    def test_learn_workflow_watch_not_implemented(self, tmp_path):
        from attune.workflow_learn import learn_workflow

        mock_wc = self._make_wc()
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = learn_workflow(patterns_dir=str(tmp_path), watch=True)
        assert result == 1

    def test_cmd_learn_delegates(self):
        from attune.workflow_learn import cmd_learn

        mock_wc = MagicMock()
        mock_wc.learn_workflow.return_value = 0
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            args = MagicMock()
            args.patterns_dir = "./patterns"
            args.analyze = None
            args.watch = False
            args.verbose = False
            result = cmd_learn(args)
        assert result == 0
        mock_wc.learn_workflow.assert_called_once()

    def test_wc_late_binding(self):
        from attune.workflow_learn import _wc

        mock_wc = MagicMock()
        with patch.dict(sys.modules, {"attune.workflow_commands": mock_wc}):
            result = _wc()
        assert result is mock_wc

    def test_bug_fix_keywords_defined(self):
        from attune.workflow_learn import _BUG_FIX_KEYWORDS

        assert "fix" in _BUG_FIX_KEYWORDS
        assert "bug" in _BUG_FIX_KEYWORDS
