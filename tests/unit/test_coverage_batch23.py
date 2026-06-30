# Copyright 2025 Smart AI Memory, LLC
# Licensed under the Apache License, Version 2.0

"""Batch 23: cost_tracker.

Coordination/conflict_resolution tests removed in v6.8.0 alongside
the `attune/coordination/` directory deletion (P1 of
`docs/specs/redis-decoupling/`).
"""

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
        record = tracker.log_request("claude-sonnet-5", 1000, 500, "summarize")
        assert record["model"] == "claude-sonnet-5"
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
        tracker.log_request("claude-sonnet-5", 100, 50, "test")
        assert len(tracker._buffer) == 1
        tracker.flush()

    def test_log_request_auto_flush_at_batch_size(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=3)
        for _ in range(3):
            tracker.log_request("claude-sonnet-5", 100, 50, "test")
        # Buffer should be flushed
        assert len(tracker._buffer) == 0

    def test_log_request_haiku_gets_cheap_tier(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-haiku-4-5", 100, 50)
        assert record["tier"] == "cheap"
        tracker.flush()

    def test_log_request_opus_gets_premium_tier(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-opus-4-8", 100, 50)
        assert record["tier"] == "premium"
        tracker.flush()

    def test_log_request_tier_override(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        record = tracker.log_request("claude-sonnet-5", 100, 50, tier="cheap")
        assert record["tier"] == "cheap"
        tracker.flush()


class TestCostTrackerCalculateCost:
    def test_calculate_cost_known_model(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        cost = tracker._calculate_cost("claude-sonnet-5", 1_000_000, 0)
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
        record = tracker.log_request("claude-haiku-4-5", 10000, 5000)
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
        tracker.log_request("claude-sonnet-5", 1000, 500, "summarize")
        summary = tracker.get_summary(days=7)
        assert summary["requests"] == 1
        tracker.flush()

    def test_summary_after_flush(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=1)
        tracker.log_request("claude-sonnet-5", 1000, 500, "summarize")
        # Auto-flushed at batch_size=1
        tracker2 = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        summary = tracker2.get_summary(days=7)
        assert summary["requests"] >= 1
        tracker2.flush()

    def test_savings_percent_nonzero(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-haiku-4-5", 100000, 50000, "summarize")
        summary = tracker.get_summary(days=7)
        assert summary["savings_percent"] >= 0
        tracker.flush()

    def test_summary_no_breakdown(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-sonnet-5", 1000, 500, "summarize")
        summary = tracker.get_summary(days=7, include_breakdown=False)
        assert "requests" in summary
        tracker.flush()


class TestCostTrackerGetReport:
    def test_get_report_returns_string(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=100)
        tracker.log_request("claude-haiku-4-5", 5000, 2000, "summarize")
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
        tracker.log_request("claude-sonnet-5", 1000, 500, "test")
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
        tracker.log_request("claude-sonnet-5", 1000, 500)
        tracker.flush()
        assert (storage / "costs.jsonl").exists()

    def test_requests_property_triggers_load(self, tmp_path):
        from attune.cost_tracker import CostTracker

        tracker = CostTracker(storage_dir=str(tmp_path / "t"), batch_size=1)
        tracker.log_request("claude-sonnet-5", 1000, 500)
        # After auto-flush, access requests property
        _ = tracker.requests
        assert tracker._requests_loaded is True


class TestModelPricingConstant:
    def test_has_anthropic_models(self):
        from attune.cost_tracker import MODEL_PRICING

        assert "claude-sonnet-5" in MODEL_PRICING
        assert "claude-haiku-4-5" in MODEL_PRICING
        assert "claude-opus-4-8" in MODEL_PRICING

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
        record = ct.log_request("claude-sonnet-5", 100, 50)
        assert "actual_cost" in record
