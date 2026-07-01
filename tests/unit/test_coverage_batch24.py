# Copyright 2025 Smart AI Memory, LLC
# Licensed under the Apache License, Version 2.0

"""Batch 24: llm/state, llm/levels, security/path_validation, metrics/prompt_metrics."""

from __future__ import annotations

import pytest

# =============================================================================
# llm/state.py
# =============================================================================


class TestPatternType:
    def test_enum_values(self):
        from attune.llm.state import PatternType

        assert PatternType.SEQUENTIAL.value == "sequential"
        assert PatternType.TEMPORAL.value == "temporal"
        assert PatternType.CONDITIONAL.value == "conditional"
        assert PatternType.PREFERENCE.value == "preference"


class TestUserPattern:
    def _make_pattern(self, confidence=0.8):
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        return UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="commit",
            action="run tests",
            confidence=confidence,
            occurrences=5,
            last_seen=datetime.now(),
        )

    def test_should_act_high_confidence_high_trust(self):
        p = self._make_pattern(confidence=0.9)
        assert p.should_act(trust_level=0.8) is True

    def test_should_act_low_confidence(self):
        p = self._make_pattern(confidence=0.5)
        assert p.should_act(trust_level=0.9) is False

    def test_should_act_low_trust(self):
        p = self._make_pattern(confidence=0.9)
        assert p.should_act(trust_level=0.4) is False

    def test_should_act_boundary_values(self):
        p = self._make_pattern(confidence=0.71)
        # confidence > 0.7 AND trust > 0.6
        assert p.should_act(trust_level=0.61) is True
        assert p.should_act(trust_level=0.6) is False


class TestCollaborationState:
    def _make_state(self, user_id="user1"):
        from attune.llm.state import CollaborationState

        return CollaborationState(user_id=user_id)

    def test_initial_trust_level(self):
        state = self._make_state()
        assert state.trust_level == 0.5

    def test_initial_success_rate_no_actions(self):
        state = self._make_state()
        assert state.success_rate == 1.0

    def test_success_rate_with_actions(self):
        state = self._make_state()
        state.successful_actions = 7
        state.failed_actions = 3
        assert state.success_rate == pytest.approx(0.7)

    def test_add_interaction_user_role(self):
        state = self._make_state()
        state.add_interaction("user", "hello", empathy_level=1)
        assert len(state.interactions) == 1
        assert len(state.level_history) == 0  # Only assistant adds to history

    def test_add_interaction_assistant_role(self):
        state = self._make_state()
        state.add_interaction("assistant", "hi", empathy_level=2)
        assert len(state.interactions) == 1
        assert 2 in state.level_history

    def test_update_trust_success(self):
        state = self._make_state()
        initial = state.trust_level
        state.update_trust("success")
        assert state.trust_level > initial
        assert state.successful_actions == 1

    def test_update_trust_failure(self):
        state = self._make_state()
        initial = state.trust_level
        state.update_trust("failure")
        assert state.trust_level < initial
        assert state.failed_actions == 1

    def test_update_trust_caps_at_1(self):
        state = self._make_state()
        state.trust_level = 0.99
        state.update_trust("success", magnitude=10.0)
        assert state.trust_level <= 1.0

    def test_update_trust_floors_at_0(self):
        state = self._make_state()
        state.trust_level = 0.01
        state.update_trust("failure", magnitude=10.0)
        assert state.trust_level >= 0.0

    def test_trust_trajectory_tracked(self):
        state = self._make_state()
        state.update_trust("success")
        state.update_trust("failure")
        assert len(state.trust_trajectory) == 2

    def test_add_pattern_new(self):
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        state = self._make_state()
        p = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="test",
            action="run",
            confidence=0.8,
            occurrences=3,
            last_seen=datetime.now(),
        )
        state.add_pattern(p)
        assert len(state.detected_patterns) == 1

    def test_add_pattern_updates_existing(self):
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        state = self._make_state()
        p1 = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="test",
            action="run",
            confidence=0.8,
            occurrences=3,
            last_seen=datetime.now(),
        )
        p2 = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="test",  # same type + trigger
            action="run",
            confidence=0.95,
            occurrences=10,
            last_seen=datetime.now(),
        )
        state.add_pattern(p1)
        state.add_pattern(p2)
        assert len(state.detected_patterns) == 1
        assert state.detected_patterns[0].confidence == 0.95

    def test_find_matching_pattern_found(self):
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        state = self._make_state()
        state.trust_level = 0.9
        p = UserPattern(
            pattern_type=PatternType.SEQUENTIAL,
            trigger="commit",
            action="push",
            confidence=0.9,
            occurrences=5,
            last_seen=datetime.now(),
        )
        state.detected_patterns.append(p)
        result = state.find_matching_pattern("please commit the changes")
        assert result is not None
        assert result.trigger == "commit"

    def test_find_matching_pattern_not_found(self):
        state = self._make_state()
        result = state.find_matching_pattern("deploy to production")
        assert result is None

    def test_get_conversation_history(self):
        state = self._make_state()
        state.add_interaction("user", "hi", 1)
        state.add_interaction("assistant", "hello", 1)
        history = state.get_conversation_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"

    def test_get_conversation_history_max_turns(self):
        state = self._make_state()
        for i in range(10):
            state.add_interaction("user", f"msg{i}", 1)
        history = state.get_conversation_history(max_turns=3)
        assert len(history) == 3

    def test_get_conversation_history_with_metadata(self):
        state = self._make_state()
        state.add_interaction("user", "hi", 1, metadata={"source": "cli"})
        history = state.get_conversation_history(include_metadata=True)
        assert "metadata" in history[0]

    def test_should_progress_level_2_always_true(self):
        state = self._make_state()
        assert state.should_progress_to_level(2) is True

    def test_should_progress_level_3_needs_trust_and_patterns(self):
        from datetime import datetime

        from attune.llm.state import PatternType, UserPattern

        state = self._make_state()
        state.trust_level = 0.4
        assert state.should_progress_to_level(3) is False

        state.trust_level = 0.7
        p = UserPattern(PatternType.SEQUENTIAL, "t", "a", 0.8, 1, datetime.now())
        state.detected_patterns.append(p)
        assert state.should_progress_to_level(3) is True

    def test_should_progress_level_5_needs_high_trust(self):
        state = self._make_state()
        state.trust_level = 0.7
        assert state.should_progress_to_level(5) is False
        state.trust_level = 0.9
        assert state.should_progress_to_level(5) is True

    def test_get_statistics(self):
        state = self._make_state()
        state.add_interaction("user", "hi", 1)
        stats = state.get_statistics()
        assert stats["user_id"] == "user1"
        assert stats["total_interactions"] == 1
        assert "trust_level" in stats


# =============================================================================
# llm/levels.py
# =============================================================================


class TestEmpathyLevel:
    def test_enum_values(self):
        from attune.llm.levels import EmpathyLevel

        assert EmpathyLevel.REACTIVE == 1
        assert EmpathyLevel.GUIDED == 2
        assert EmpathyLevel.PROACTIVE == 3
        assert EmpathyLevel.ANTICIPATORY == 4
        assert EmpathyLevel.SYSTEMS == 5

    def test_get_description_all_levels(self):
        from attune.llm.levels import EmpathyLevel

        for level in range(1, 6):
            desc = EmpathyLevel.get_description(level)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_get_description_unknown_level(self):
        from attune.llm.levels import EmpathyLevel

        desc = EmpathyLevel.get_description(99)
        assert "Unknown" in desc

    def test_get_system_prompt_all_levels(self):
        from attune.llm.levels import EmpathyLevel

        for level in range(1, 6):
            prompt = EmpathyLevel.get_system_prompt(level)
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_get_temperature_recommendation(self):
        from attune.llm.levels import EmpathyLevel

        t1 = EmpathyLevel.get_temperature_recommendation(1)
        t4 = EmpathyLevel.get_temperature_recommendation(4)
        assert 0 < t4 < t1  # Higher levels have lower temperature

    def test_get_temperature_unknown_level(self):
        from attune.llm.levels import EmpathyLevel

        t = EmpathyLevel.get_temperature_recommendation(99)
        assert t == 0.7  # Default

    def test_get_required_context(self):
        from attune.llm.levels import EmpathyLevel

        ctx1 = EmpathyLevel.get_required_context(1)
        assert ctx1["conversation_history"] is False

        ctx3 = EmpathyLevel.get_required_context(3)
        assert ctx3["user_patterns"] is True

        ctx5 = EmpathyLevel.get_required_context(5)
        assert ctx5["pattern_library"] is True

    def test_get_max_tokens_recommendation(self):
        from attune.llm.levels import EmpathyLevel

        t1 = EmpathyLevel.get_max_tokens_recommendation(1)
        t4 = EmpathyLevel.get_max_tokens_recommendation(4)
        assert t4 > t1

    def test_should_use_json_mode(self):
        from attune.llm.levels import EmpathyLevel

        assert EmpathyLevel.should_use_json_mode(3) is False
        assert EmpathyLevel.should_use_json_mode(4) is True
        assert EmpathyLevel.should_use_json_mode(5) is True

    def test_get_typical_use_cases(self):
        from attune.llm.levels import EmpathyLevel

        for level in range(1, 6):
            cases = EmpathyLevel.get_typical_use_cases(level)
            assert isinstance(cases, list)
            assert len(cases) > 0


# =============================================================================
# security/path_validation.py
# =============================================================================


class TestValidateFilePath:
    def test_valid_path_returns_path_object(self, tmp_path):
        from pathlib import Path

        from attune.security.path_validation import _validate_file_path

        result = _validate_file_path(str(tmp_path / "test.txt"))
        assert isinstance(result, Path)

    def test_empty_path_raises(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises(ValueError, match="non-empty"):
            _validate_file_path("")

    def test_none_raises(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises((ValueError, TypeError)):
            _validate_file_path(None)  # type: ignore

    def test_null_byte_raises(self):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises(ValueError, match="null bytes"):
            _validate_file_path("/tmp/test\x00.txt")

    def test_allowed_dir_inside_succeeds(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        result = _validate_file_path(str(tmp_path / "file.txt"), allowed_dir=str(tmp_path))
        assert str(tmp_path) in str(result)

    def test_allowed_dir_outside_raises(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        with pytest.raises(ValueError, match="outside allowed"):
            _validate_file_path("/tmp/outside.txt", allowed_dir=str(tmp_path))

    def test_system_path_raises(self):
        import sys

        from attune.security.path_validation import _validate_file_path

        if sys.platform != "win32":
            with pytest.raises(ValueError, match="system directory"):
                _validate_file_path("/etc/passwd")

    def test_regular_path_succeeds(self, tmp_path):
        from attune.security.path_validation import _validate_file_path

        path = tmp_path / "myfile.json"
        result = _validate_file_path(str(path))
        assert result.name == "myfile.json"


# =============================================================================
# metrics/prompt_metrics.py
# =============================================================================


def _make_metric(**overrides):
    from attune.metrics.prompt_metrics import PromptMetrics

    defaults = {
        "timestamp": "2026-01-01T10:00:00",
        "workflow": "code_review",
        "agent_role": "Code Reviewer",
        "task_description": "Review code",
        "model": "claude-sonnet-5",
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500,
        "latency_ms": 200.0,
        "retry_count": 0,
        "parsing_success": True,
        "validation_success": True,
        "error_message": None,
        "xml_structure_used": True,
    }
    defaults.update(overrides)
    return PromptMetrics(**defaults)


class TestPromptMetrics:
    def test_to_dict_roundtrip(self):
        m = _make_metric()
        d = m.to_dict()
        assert d["workflow"] == "code_review"
        assert d["total_tokens"] == 1500

    def test_from_dict_roundtrip(self):
        from attune.metrics.prompt_metrics import PromptMetrics

        m = _make_metric()
        d = m.to_dict()
        m2 = PromptMetrics.from_dict(d)
        assert m2.workflow == m.workflow
        assert m2.total_tokens == m.total_tokens

    def test_to_dict_keys(self):
        m = _make_metric()
        d = m.to_dict()
        assert "timestamp" in d
        assert "latency_ms" in d
        assert "parsing_success" in d


class TestMetricsTracker:
    def test_init_creates_file(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        MetricsTracker(metrics_file=metrics_file)
        assert (tmp_path / "metrics.json").exists()

    def test_log_metric_appends(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        tracker.log_metric(_make_metric())
        tracker.log_metric(_make_metric(workflow="bug_predict"))
        metrics = tracker.get_metrics()
        assert len(metrics) == 2

    def test_get_metrics_filter_by_workflow(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        tracker.log_metric(_make_metric(workflow="code_review"))
        tracker.log_metric(_make_metric(workflow="bug_predict"))
        results = tracker.get_metrics(workflow="code_review")
        assert len(results) == 1
        assert results[0].workflow == "code_review"

    def test_get_metrics_empty(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        results = tracker.get_metrics()
        assert results == []

    def test_get_summary_empty(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        summary = tracker.get_summary()
        assert summary["total_prompts"] == 0

    def test_get_summary_with_data(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        tracker.log_metric(_make_metric(total_tokens=1000, latency_ms=100.0, retry_count=0))
        tracker.log_metric(_make_metric(total_tokens=2000, latency_ms=200.0, retry_count=1))
        summary = tracker.get_summary()
        assert summary["total_prompts"] == 2
        assert summary["avg_tokens"] == pytest.approx(1500.0)
        assert summary["avg_latency_ms"] == pytest.approx(150.0)
        assert summary["success_rate"] == 1.0
        assert summary["retry_rate"] == pytest.approx(0.5)

    def test_get_summary_filter_by_workflow(self, tmp_path):
        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        tracker.log_metric(_make_metric(workflow="code_review", total_tokens=500))
        tracker.log_metric(_make_metric(workflow="bug_predict", total_tokens=1000))
        summary = tracker.get_summary(workflow="code_review")
        assert summary["total_prompts"] == 1
        assert summary["avg_tokens"] == pytest.approx(500.0)

    def test_get_metrics_date_filter(self, tmp_path):
        from datetime import datetime

        from attune.metrics.prompt_metrics import MetricsTracker

        metrics_file = str(tmp_path / "metrics.json")
        tracker = MetricsTracker(metrics_file=metrics_file)
        tracker.log_metric(_make_metric(timestamp="2025-01-01T10:00:00"))
        tracker.log_metric(_make_metric(timestamp="2026-06-01T10:00:00"))
        results = tracker.get_metrics(start_date=datetime(2026, 1, 1))
        assert len(results) == 1
        assert "2026" in results[0].timestamp
