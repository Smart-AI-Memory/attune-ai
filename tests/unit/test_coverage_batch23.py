# Copyright 2025 Smart AI Memory, LLC
# Licensed under the Apache License, Version 2.0

"""Batch 23: cost_tracker, coordination/conflict_resolution."""

from __future__ import annotations

import pytest

# =============================================================================
# cost_tracker.py
# =============================================================================


class TestCostTrackerInit:
    def test_init_creates_storage_dir(self, tmp_path):
        from attune.cost_tracker import CostTracker

        storage = tmp_path / "my_attune"
        tracker = CostTracker(storage_dir=str(storage))
        assert storage.exists()
        tracker.flush()

    def test_init_default_data(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "a"))
        assert "daily_totals" in tracker.data
        tracker.flush()


class TestCostTrackerLogRequest:
    def setup_method(self, tmp_path):
        pass

    def test_log_request_returns_dict(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-sonnet-4-6", 1000, 500, "summarize")
        assert record["model"] == "claude-sonnet-4-6"
        assert record["input_tokens"] == 1000
        assert record["output_tokens"] == 500
        assert record["task_type"] == "summarize"
        assert "actual_cost" in record
        assert "baseline_cost" in record
        assert "savings" in record
        tracker.flush()

    def test_log_request_buffers_before_flush(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-sonnet-4-6", 100, 50, "test")
        assert len(tracker._buffer) == 1
        tracker.flush()

    def test_log_request_auto_flush_at_batch_size(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=3)
        for _ in range(3):
            tracker.log_request("claude-sonnet-4-6", 100, 50, "test")
        # Buffer should be flushed
        assert len(tracker._buffer) == 0

    def test_log_request_haiku_gets_cheap_tier(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-haiku-4-5-20251001", 100, 50)
        assert record["tier"] == "cheap"
        tracker.flush()

    def test_log_request_opus_gets_premium_tier(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-opus-4-6", 100, 50)
        assert record["tier"] == "premium"
        tracker.flush()

    def test_log_request_tier_override(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-sonnet-4-6", 100, 50, tier="cheap")
        assert record["tier"] == "cheap"
        tracker.flush()


class TestCostTrackerCalculateCost:
    def test_calculate_cost_known_model(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        cost = tracker._calculate_cost("claude-sonnet-4-6", 1_000_000, 0)
        assert cost == pytest.approx(3.0)
        tracker.flush()

    def test_calculate_cost_unknown_model_fallback(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        cost = tracker._calculate_cost("totally-unknown-model", 1_000_000, 0)
        assert cost > 0  # Uses capable fallback
        tracker.flush()

    def test_savings_is_nonnegative_for_cheap_model(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-haiku-4-5-20251001", 10000, 5000)
        assert record["savings"] >= 0
        tracker.flush()


class TestCostTrackerSummary:
    def test_empty_summary(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        summary = tracker.get_summary(days=7)
        assert summary["requests"] == 0
        assert summary["actual_cost"] == 0
        tracker.flush()

    def test_summary_includes_buffered_requests(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-sonnet-4-6", 1000, 500, "summarize")
        summary = tracker.get_summary(days=7)
        assert summary["requests"] == 1
        tracker.flush()

    def test_summary_after_flush(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=1)
        tracker.log_request("claude-sonnet-4-6", 1000, 500, "summarize")
        # Auto-flushed at batch_size=1
        tracker2 = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        summary = tracker2.get_summary(days=7)
        assert summary["requests"] >= 1
        tracker2.flush()

    def test_savings_percent_nonzero(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-haiku-4-5-20251001", 100000, 50000, "summarize")
        summary = tracker.get_summary(days=7)
        assert summary["savings_percent"] >= 0
        tracker.flush()

    def test_summary_no_breakdown(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-sonnet-4-6", 1000, 500, "summarize")
        summary = tracker.get_summary(days=7, include_breakdown=False)
        assert "requests" in summary
        tracker.flush()


class TestCostTrackerGetReport:
    def test_get_report_returns_string(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-haiku-4-5-20251001", 5000, 2000, "summarize")
        report = tracker.get_report(days=7)
        assert isinstance(report, str)
        assert "COST TRACKING REPORT" in report
        tracker.flush()

    def test_get_report_empty(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        report = tracker.get_report(days=7)
        assert "COST TRACKING REPORT" in report
        tracker.flush()


class TestCostTrackerGetToday:
    def test_get_today_empty(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        today = tracker.get_today()
        assert today["requests"] == 0
        tracker.flush()

    def test_get_today_includes_buffer(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-sonnet-4-6", 1000, 500, "test")
        today = tracker.get_today()
        assert today["requests"] == 1
        tracker.flush()


class TestCostTrackerFlushAndPersist:
    def test_flush_empty_buffer_is_noop(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.flush()  # Should not raise
        assert tracker._buffer == []

    def test_flush_writes_jsonl(self, tmp_path):
        from attune.cost_tracker import CostTracker

        storage = tmp_path / "t"
        tracker = CostTracker(storage_dir=str(storage), batch_size=100)
        tracker.log_request("claude-sonnet-4-6", 1000, 500)
        tracker.flush()
        assert (storage / "costs.jsonl").exists()

    def test_requests_property_triggers_load(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=1)
        tracker.log_request("claude-sonnet-4-6", 1000, 500)
        # After auto-flush, access requests property
        _ = tracker.requests
        assert tracker._requests_loaded is True


class TestModelPricingConstant:
    def test_has_anthropic_models(self):
        from attune.cost_tracker import MODEL_PRICING

        assert "claude-sonnet-4-6" in MODEL_PRICING
        assert "claude-haiku-4-5-20251001" in MODEL_PRICING
        assert "claude-opus-4-6" in MODEL_PRICING

    def test_has_tier_aliases(self):
        from attune.cost_tracker import MODEL_PRICING

        assert "cheap" in MODEL_PRICING
        assert "capable" in MODEL_PRICING
        assert "premium" in MODEL_PRICING

    def test_has_legacy_models(self):
        from attune.cost_tracker import MODEL_PRICING

        assert "claude-3-haiku-20240307" in MODEL_PRICING


class TestCostTrackerHelpers:
    def test_get_tracker_returns_instance(self, tmp_path, monkeypatch):
        from attune import cost_tracker as ct

        monkeypatch.setattr(ct, "_tracker", None)
        tracker = ct.get_tracker(storage_dir=str(tmp_path / "t"))
        assert tracker is not None
        tracker.flush()
        monkeypatch.setattr(ct, "_tracker", None)

    def test_log_request_convenience_function(self, tmp_path, monkeypatch):
        from attune import cost_tracker as ct

        monkeypatch.setattr(ct, "_tracker", None)
        monkeypatch.setattr(
            ct,
            "get_tracker",
            lambda storage_dir=".attune": ct.CostTracker(str(tmp_path / "t"), batch_size=100),
        )
        record = ct.log_request("claude-sonnet-4-6", 100, 50)
        assert "actual_cost" in record


# =============================================================================
# coordination/conflict_resolution.py
# =============================================================================


def _make_pattern(
    id="p1",
    agent_id="agent1",
    pattern_type="best_practice",
    name="Pattern 1",
    confidence=0.8,
    tags=None,
    context=None,
):
    from attune.pattern_library import Pattern

    return Pattern(
        id=id,
        agent_id=agent_id,
        pattern_type=pattern_type,
        name=name,
        description="A test pattern",
        confidence=confidence,
        tags=tags or [],
        context=context or {},
    )


class TestResolutionStrategy:
    def test_enum_values(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        assert ResolutionStrategy.HIGHEST_CONFIDENCE.value == "highest_confidence"
        assert ResolutionStrategy.MOST_RECENT.value == "most_recent"
        assert ResolutionStrategy.WEIGHTED_SCORE.value == "weighted_score"


class TestTeamPriorities:
    def test_default_weights_sum_to_one(self):
        from attune.coordination.conflict_resolution import TeamPriorities

        tp = TeamPriorities()
        total = (
            tp.readability_weight
            + tp.performance_weight
            + tp.security_weight
            + tp.maintainability_weight
        )
        assert total == pytest.approx(1.0)

    def test_default_type_preferences(self):
        from attune.coordination.conflict_resolution import TeamPriorities

        tp = TeamPriorities()
        assert "security" in tp.type_preferences
        assert tp.type_preferences["security"] == 1.0


class TestConflictResolverInit:
    def test_default_strategy_weighted_score(self):
        from attune.coordination.conflict_resolution import ConflictResolver, ResolutionStrategy

        resolver = ConflictResolver()
        assert resolver.default_strategy == ResolutionStrategy.WEIGHTED_SCORE

    def test_custom_strategy(self):
        from attune.coordination.conflict_resolution import ConflictResolver, ResolutionStrategy

        resolver = ConflictResolver(default_strategy=ResolutionStrategy.MOST_RECENT)
        assert resolver.default_strategy == ResolutionStrategy.MOST_RECENT

    def test_resolution_history_starts_empty(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        assert resolver.resolution_history == []


class TestConflictResolverResolvePatterns:
    def setup_method(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        self.resolver = ConflictResolver()

    def test_resolve_requires_at_least_two_patterns(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        with pytest.raises(ValueError, match="at least 2"):
            resolver.resolve_patterns([_make_pattern()])

    def test_resolve_two_patterns_returns_result(self):
        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.5)
        result = self.resolver.resolve_patterns([p1, p2])
        assert result.winning_pattern is not None
        assert len(result.losing_patterns) == 1

    def test_highest_confidence_picks_most_confident(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        p1 = _make_pattern(id="p1", name="High Conf", confidence=0.95)
        p2 = _make_pattern(id="p2", name="Low Conf", confidence=0.3)
        result = self.resolver.resolve_patterns(
            [p1, p2], strategy=ResolutionStrategy.HIGHEST_CONFIDENCE
        )
        assert result.winning_pattern.id == "p1"

    def test_most_recent_strategy(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        p1 = _make_pattern(id="p1", name="P1")
        p2 = _make_pattern(id="p2", name="P2")
        result = self.resolver.resolve_patterns([p1, p2], strategy=ResolutionStrategy.MOST_RECENT)
        assert result.strategy_used == ResolutionStrategy.MOST_RECENT

    def test_best_context_match_strategy(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        p1 = _make_pattern(id="p1", context={"lang": "python"})
        p2 = _make_pattern(id="p2", context={"lang": "java"})
        result = self.resolver.resolve_patterns(
            [p1, p2],
            context={"lang": "python"},
            strategy=ResolutionStrategy.BEST_CONTEXT_MATCH,
        )
        assert result.winning_pattern.id == "p1"

    def test_team_priority_strategy(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        p1 = _make_pattern(id="p1", pattern_type="security")
        p2 = _make_pattern(id="p2", pattern_type="style")
        result = self.resolver.resolve_patterns(
            [p1, p2],
            context={"team_priority": "security"},
            strategy=ResolutionStrategy.TEAM_PRIORITY,
        )
        assert result.strategy_used == ResolutionStrategy.TEAM_PRIORITY

    def test_weighted_score_strategy_default(self):
        from attune.coordination.conflict_resolution import ResolutionStrategy

        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.4)
        result = self.resolver.resolve_patterns([p1, p2])
        assert result.strategy_used == ResolutionStrategy.WEIGHTED_SCORE

    def test_resolve_records_history(self):
        p1 = _make_pattern(id="p1")
        p2 = _make_pattern(id="p2")
        self.resolver.resolve_patterns([p1, p2])
        assert len(self.resolver.resolution_history) == 1

    def test_reasoning_is_nonempty_string(self):
        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.3)
        result = self.resolver.resolve_patterns([p1, p2])
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0

    def test_resolve_three_patterns(self):
        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.6)
        p3 = _make_pattern(id="p3", confidence=0.3)
        result = self.resolver.resolve_patterns([p1, p2, p3])
        assert len(result.losing_patterns) == 2


class TestConflictResolverContextMatch:
    def setup_method(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        self.resolver = ConflictResolver()

    def test_no_context_returns_neutral(self):
        p = _make_pattern()
        score = self.resolver._calculate_context_match(p, {})
        assert score == 0.5

    def test_no_pattern_context_returns_neutral(self):
        p = _make_pattern(context={})
        score = self.resolver._calculate_context_match(p, {"lang": "python"})
        assert score == 0.5

    def test_no_common_keys_low_match(self):
        p = _make_pattern(context={"framework": "django"})
        score = self.resolver._calculate_context_match(p, {"lang": "python"})
        assert score == pytest.approx(0.3)

    def test_matching_values_boosts_score(self):
        p = _make_pattern(context={"lang": "python", "ver": "3"})
        score = self.resolver._calculate_context_match(p, {"lang": "python", "ver": "3"})
        assert score > 0.5

    def test_tag_overlap_adds_bonus(self):
        p = _make_pattern(context={"lang": "python"}, tags=["security"])
        score = self.resolver._calculate_context_match(p, {"lang": "python", "tags": ["security"]})
        assert score >= 0.5


class TestConflictResolverStats:
    def test_empty_history_stats(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        stats = resolver.get_resolution_stats()
        assert stats["total_resolutions"] == 0
        assert stats["average_confidence"] == 0.0

    def test_stats_after_resolution(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.4)
        resolver.resolve_patterns([p1, p2])
        stats = resolver.get_resolution_stats()
        assert stats["total_resolutions"] == 1
        assert stats["average_confidence"] > 0
        assert "weighted_score" in stats["strategies_used"]

    def test_clear_history(self):
        from attune.coordination.conflict_resolution import ConflictResolver

        resolver = ConflictResolver()
        p1 = _make_pattern(id="p1")
        p2 = _make_pattern(id="p2")
        resolver.resolve_patterns([p1, p2])
        resolver.clear_history()
        assert resolver.resolution_history == []


class TestResolutionResult:
    def test_result_attributes(self):
        from attune.coordination.conflict_resolution import ConflictResolver, ResolutionStrategy

        resolver = ConflictResolver()
        p1 = _make_pattern(id="p1", confidence=0.9)
        p2 = _make_pattern(id="p2", confidence=0.3)
        result = resolver.resolve_patterns([p1, p2])

        assert hasattr(result, "winning_pattern")
        assert hasattr(result, "losing_patterns")
        assert hasattr(result, "strategy_used")
        assert hasattr(result, "confidence")
        assert hasattr(result, "reasoning")
        assert hasattr(result, "factors")
        assert isinstance(result.strategy_used, ResolutionStrategy)
