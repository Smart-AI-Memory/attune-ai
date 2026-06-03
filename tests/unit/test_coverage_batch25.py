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
            model="claude-sonnet-4-6",
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
            model="claude-sonnet-4-6",
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
            model="claude-sonnet-4-6",
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
            model="claude-sonnet-4-6",
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
            model="claude-sonnet-4-6",
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
            model="claude-sonnet-4-6",
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
                model="claude-sonnet-4-6",
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


# =============================================================================
# trust/circuit_breaker.py
# =============================================================================


class TestTrustState:
    def test_enum_values(self):
        from attune.trust.circuit_breaker import TrustState

        assert TrustState.FULL_AUTONOMY.value == "full_autonomy"
        assert TrustState.REDUCED_AUTONOMY.value == "reduced_autonomy"
        assert TrustState.SUPERVISED.value == "supervised"


class TestTrustDamageType:
    def test_enum_values(self):
        from attune.trust.circuit_breaker import TrustDamageType

        assert TrustDamageType.WRONG_ANSWER.value == "wrong_answer"
        assert TrustDamageType.REPETITIVE_ERROR.value == "repetitive_error"


class TestTrustDamageEvent:
    def test_string_event_type_coerced(self):
        from attune.trust.circuit_breaker import TrustDamageEvent, TrustDamageType

        event = TrustDamageEvent(event_type="wrong_answer")
        assert event.event_type == TrustDamageType.WRONG_ANSWER

    def test_enum_event_type_preserved(self):
        from attune.trust.circuit_breaker import TrustDamageEvent, TrustDamageType

        event = TrustDamageEvent(event_type=TrustDamageType.SLOW_RESPONSE)
        assert event.event_type == TrustDamageType.SLOW_RESPONSE


class TestTrustConfig:
    def test_defaults(self):
        from attune.trust.circuit_breaker import TrustConfig

        config = TrustConfig()
        assert config.damage_threshold == 3
        assert config.recovery_period_hours == 24.0
        assert config.supervised_successes_required == 5
        assert config.domain_isolation is True

    def test_severity_weights_present(self):
        from attune.trust.circuit_breaker import TrustConfig, TrustDamageType

        config = TrustConfig()
        assert TrustDamageType.WRONG_ANSWER in config.severity_weights
        assert TrustDamageType.REPETITIVE_ERROR in config.severity_weights
        # Repetitive error is most damaging
        assert config.severity_weights[TrustDamageType.REPETITIVE_ERROR] > 1.0


class TestTrustCircuitBreakerInit:
    def test_initial_state_full_autonomy(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        assert breaker.state == TrustState.FULL_AUTONOMY

    def test_initial_can_act_freely(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        assert breaker.can_act_freely is True

    def test_initial_damage_score_zero(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        assert breaker.damage_score == 0.0


class TestTrustCircuitBreakerRecordDamage:
    def _make_breaker(self, threshold=3):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustConfig

        config = TrustConfig(damage_threshold=threshold)
        return TrustCircuitBreaker(user_id="user1", config=config)

    def test_single_damage_below_threshold(self):
        from attune.trust.circuit_breaker import TrustState

        breaker = self._make_breaker(threshold=10)
        breaker.record_damage("wrong_answer")
        assert breaker.state == TrustState.FULL_AUTONOMY

    def test_damage_above_threshold_transitions_state(self):
        from attune.trust.circuit_breaker import TrustDamageType, TrustState

        breaker = self._make_breaker(threshold=1)
        breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)
        assert breaker.state == TrustState.REDUCED_AUTONOMY

    def test_damage_score_increases_with_events(self):
        breaker = self._make_breaker(threshold=100)
        breaker.record_damage("wrong_answer")
        score1 = breaker.damage_score
        breaker.record_damage("wrong_answer")
        score2 = breaker.damage_score
        assert score2 > score1

    def test_string_event_type_accepted(self):
        from attune.trust.circuit_breaker import TrustState

        breaker = self._make_breaker(threshold=100)
        new_state = breaker.record_damage("slow_response")
        assert new_state == TrustState.FULL_AUTONOMY


class TestTrustCircuitBreakerRecordSuccess:
    def test_success_in_supervised_mode_increments_counter(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustConfig, TrustState

        config = TrustConfig(
            damage_threshold=1,
            recovery_period_hours=0.0,
            supervised_successes_required=3,
        )
        breaker = TrustCircuitBreaker(user_id="user1", config=config)
        # Force to supervised state
        breaker._state = TrustState.SUPERVISED
        breaker.record_success()
        assert breaker._supervised_successes == 1

    def test_enough_successes_transitions_to_full_autonomy(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustConfig, TrustState

        config = TrustConfig(
            damage_threshold=1,
            recovery_period_hours=0.0,
            supervised_successes_required=2,
        )
        breaker = TrustCircuitBreaker(user_id="user1", config=config)
        breaker._state = TrustState.SUPERVISED
        breaker.record_success()
        breaker.record_success()
        assert breaker._state == TrustState.FULL_AUTONOMY


class TestTrustCircuitBreakerShouldRequireConfirmation:
    def test_full_autonomy_no_confirmation(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        assert breaker.should_require_confirmation("file_write") is False

    def test_reduced_autonomy_always_requires(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.REDUCED_AUTONOMY
        assert breaker.should_require_confirmation("suggest") is True
        assert breaker.should_require_confirmation("file_write") is True

    def test_supervised_mode_high_impact_requires(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.SUPERVISED
        assert breaker.should_require_confirmation("file_write") is True

    def test_supervised_mode_low_impact_no_confirmation(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.SUPERVISED
        assert breaker.should_require_confirmation("suggest") is False


class TestTrustCircuitBreakerGetAutonomyLevel:
    def test_get_autonomy_level_full(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        info = breaker.get_autonomy_level()
        assert info["state"] == "full_autonomy"
        assert info["can_act_freely"] is True

    def test_get_autonomy_level_reduced(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.REDUCED_AUTONOMY
        info = breaker.get_autonomy_level()
        assert info["state"] == "reduced_autonomy"
        assert info["can_act_freely"] is False

    def test_get_autonomy_level_supervised(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.SUPERVISED
        info = breaker.get_autonomy_level()
        assert info["state"] == "supervised"


class TestTrustCircuitBreakerReset:
    def test_reset_returns_to_full_autonomy(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.REDUCED_AUTONOMY
        breaker.reset()
        assert breaker._state == TrustState.FULL_AUTONOMY

    def test_reset_clears_damage_events(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker.record_damage("wrong_answer")
        breaker.reset()
        assert len(breaker._damage_events) == 0


class TestTrustCircuitBreakerRecoveryProgress:
    def test_full_autonomy_progress_is_one(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker

        breaker = TrustCircuitBreaker(user_id="user1")
        progress = breaker._get_recovery_progress()
        assert progress["status"] == "full_trust"
        assert progress["progress"] == 1.0

    def test_reduced_autonomy_progress(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.REDUCED_AUTONOMY
        progress = breaker._get_recovery_progress()
        assert progress["status"] in ("cooling_off", "ready_for_supervised")

    def test_supervised_progress(self):
        from attune.trust.circuit_breaker import TrustCircuitBreaker, TrustState

        breaker = TrustCircuitBreaker(user_id="user1")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 2
        progress = breaker._get_recovery_progress()
        assert progress["status"] == "supervised_testing"
        assert progress["successes"] == 2
