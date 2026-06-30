# Copyright 2025 Smart AI Memory, LLC
# Licensed under the Apache License, Version 2.0

"""Batch 25: telemetry/usage_tracker, trust/circuit_breaker."""

from __future__ import annotations

import pytest

# =============================================================================
# telemetry/usage_tracker.py
# =============================================================================


class TestUsageTrackerInit:
    def test_init_creates_directory(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        telemetry_dir = tmp_path / "telemetry"
        tracker = UsageTracker(telemetry_dir=telemetry_dir)
        assert telemetry_dir.exists()
        tracker.flush()

    def test_singleton_get_instance(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        UsageTracker._instance = None
        tracker1 = UsageTracker.get_instance(telemetry_dir=tmp_path / "t1")
        tracker2 = UsageTracker.get_instance(telemetry_dir=tmp_path / "t2")
        assert tracker1 is tracker2
        UsageTracker._instance = None

    def test_empty_day_structure(self):
        from attune.telemetry.usage_tracker import UsageTracker

        day = UsageTracker._empty_day()
        assert day["calls"] == 0
        assert day["cost"] == 0.0
        assert "by_tier" in day
        assert "by_workflow" in day

    def test_utcnow_returns_datetime(self):
        from datetime import datetime

        from attune.telemetry.usage_tracker import UsageTracker

        dt = UsageTracker._utcnow()
        assert isinstance(dt, datetime)

    def test_utcnow_iso_returns_string(self):
        from attune.telemetry.usage_tracker import UsageTracker

        s = UsageTracker._utcnow_iso()
        assert isinstance(s, str)
        assert "T" in s


class TestUsageTrackerTrackLLMCall:
    def _make_tracker(self, tmp_path, buffer_size=100):
        from attune.telemetry.usage_tracker import UsageTracker

        return UsageTracker(telemetry_dir=tmp_path / "tel", buffer_size=buffer_size)

    def test_track_llm_call_adds_to_buffer(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="code-review",
            stage="analysis",
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 500, "output": 200},
            cache_hit=False,
            cache_type=None,
            duration_ms=250,
        )
        assert len(tracker._buffer) == 1
        tracker.flush()

    def test_track_llm_call_with_cache_hit(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="code-review",
            stage=None,
            tier="CHEAP",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.0001,
            tokens={"input": 200, "output": 50},
            cache_hit=True,
            cache_type="hash",
            duration_ms=100,
        )
        assert tracker._buffer[0]["cache"]["hit"] is True
        assert tracker._buffer[0]["cache"]["type"] == "hash"
        tracker.flush()

    def test_track_llm_call_with_prompt_cache(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="doc-gen",
            stage="generate",
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=0.002,
            tokens={"input": 1000, "output": 500},
            cache_hit=False,
            cache_type=None,
            duration_ms=500,
            prompt_cache_hit=True,
            prompt_cache_creation_tokens=200,
            prompt_cache_read_tokens=800,
        )
        entry = tracker._buffer[0]
        assert "prompt_cache" in entry
        assert entry["prompt_cache"]["hit"] is True
        tracker.flush()

    def test_track_llm_call_auto_flush_at_buffer_size(self, tmp_path):
        tracker = self._make_tracker(tmp_path, buffer_size=3)
        for _ in range(3):
            tracker.track_llm_call(
                workflow="test",
                stage=None,
                tier="CHEAP",
                model="claude-haiku-4-5",
                provider="anthropic",
                cost=0.0001,
                tokens={"input": 100, "output": 50},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )
        # Should have auto-flushed
        assert len(tracker._buffer) == 0


class TestUsageTrackerFlush:
    def _make_tracker(self, tmp_path, buffer_size=100):
        from attune.telemetry.usage_tracker import UsageTracker

        return UsageTracker(telemetry_dir=tmp_path / "tel", buffer_size=buffer_size)

    def test_flush_empty_buffer_returns_zero(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        assert tracker.flush() == 0

    def test_flush_writes_to_disk(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=200,
        )
        written = tracker.flush()
        assert written == 1
        assert tracker.usage_file.exists()

    def test_flush_updates_daily_summary(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=0.005,
            tokens={"input": 200, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=300,
        )
        tracker.flush()
        assert len(tracker._daily_summary) > 0


class TestUsageTrackerGetStats:
    def _make_tracker(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        return UsageTracker(telemetry_dir=tmp_path / "tel", buffer_size=100)

    def test_get_stats_empty(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        stats = tracker.get_stats(days=7)
        assert stats["total_calls"] == 0
        assert stats["total_cost"] == 0.0

    def test_get_stats_with_data(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="code-review",
            stage="analysis",
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=1.50,  # large enough to survive round(..., 2)
            tokens={"input": 500, "output": 200},
            cache_hit=False,
            cache_type=None,
            duration_ms=250,
        )
        tracker.flush()
        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] == 1
        assert stats["total_cost"] > 0

    def test_get_stats_includes_buffer(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CHEAP",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.0001,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type=None,
            duration_ms=100,
        )
        # Don't flush — stats should include buffer
        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] >= 1

    def test_get_stats_cache_hit_rate(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CHEAP",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.0001,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type=None,
            duration_ms=100,
        )
        tracker.flush()
        stats = tracker.get_stats(days=30)
        assert stats["cache_hit_rate"] == 100.0


class TestUsageTrackerGetRecentEntries:
    def _make_tracker(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        return UsageTracker(telemetry_dir=tmp_path / "tel", buffer_size=100)

    def test_get_recent_entries_empty(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        entries = tracker.get_recent_entries(limit=10)
        assert entries == []

    def test_get_recent_entries_from_buffer(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CAPABLE",
            model="claude-sonnet-5",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=200,
        )
        entries = tracker.get_recent_entries(limit=10)
        assert len(entries) == 1

    def test_get_recent_entries_limit(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        for _ in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage=None,
                tier="CAPABLE",
                model="claude-sonnet-5",
                provider="anthropic",
                cost=0.001,
                tokens={"input": 100, "output": 50},
                cache_hit=False,
                cache_type=None,
                duration_ms=200,
            )
        tracker.flush()
        entries = tracker.get_recent_entries(limit=3)
        assert len(entries) == 3


class TestUsageTrackerCalculateSavings:
    def _make_tracker(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        return UsageTracker(telemetry_dir=tmp_path / "tel", buffer_size=100)

    def test_calculate_savings_empty(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        savings = tracker.calculate_savings(days=30)
        assert savings["actual_cost"] == 0.0
        assert savings["total_calls"] == 0

    def test_calculate_savings_with_data(self, tmp_path):
        tracker = self._make_tracker(tmp_path)
        tracker.track_llm_call(
            workflow="test",
            stage=None,
            tier="CHEAP",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 1000, "output": 500},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )
        tracker.flush()
        savings = tracker.calculate_savings(days=30)
        assert savings["actual_cost"] >= 0
        assert "tier_distribution" in savings
        assert "savings_percent" in savings


class TestUsageTrackerHashUserId:
    def test_hash_returns_16_char_string(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        tracker = UsageTracker(telemetry_dir=tmp_path / "tel")
        hashed = tracker._hash_user_id("test_user")
        assert isinstance(hashed, str)
        assert len(hashed) == 16

    def test_same_input_same_output(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        tracker = UsageTracker(telemetry_dir=tmp_path / "tel")
        h1 = tracker._hash_user_id("alice")
        h2 = tracker._hash_user_id("alice")
        assert h1 == h2

    def test_different_inputs_different_outputs(self, tmp_path):
        from attune.telemetry.usage_tracker import UsageTracker

        tracker = UsageTracker(telemetry_dir=tmp_path / "tel")
        h1 = tracker._hash_user_id("alice")
        h2 = tracker._hash_user_id("bob")
        assert h1 != h2


class TestUsageTrackerAccumulateEntry:
    def test_accumulate_basic_entry(self):
        from attune.telemetry.usage_tracker import UsageTracker

        acc = UsageTracker._empty_day()
        entry = {
            "ts": "2026-01-01T10:00:00Z",
            "cost": 0.001,
            "tokens": {"input": 100, "output": 50},
            "cache": {"hit": True},
            "tier": "CAPABLE",
            "workflow": "test",
            "provider": "anthropic",
        }
        UsageTracker._accumulate_entry(acc, entry)
        assert acc["calls"] == 1
        assert acc["cost"] == pytest.approx(0.001)
        assert acc["tokens_in"] == 100
        assert acc["tokens_out"] == 50
        assert acc["cache_hits"] == 1
        assert acc["by_tier"]["CAPABLE"] == pytest.approx(0.001)

    def test_accumulate_cache_miss(self):
        from attune.telemetry.usage_tracker import UsageTracker

        acc = UsageTracker._empty_day()
        entry = {
            "cost": 0.0,
            "tokens": {"input": 0, "output": 0},
            "cache": {"hit": False},
            "tier": "CHEAP",
            "workflow": "test",
            "provider": "anthropic",
        }
        UsageTracker._accumulate_entry(acc, entry)
        assert acc["cache_misses"] == 1
        assert acc["cache_hits"] == 0
