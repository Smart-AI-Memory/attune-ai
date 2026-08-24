"""Unit tests for Feedback Loop (Pattern 6).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from attune.telemetry.feedback_loop import (
    FeedbackEntry,
    FeedbackLoop,
    ModelTier,
    QualityStats,
    TierRecommendation,
    _InMemoryStore,
)


class TestFeedbackEntry:
    """Test FeedbackEntry dataclass."""

    def test_feedback_entry_creation(self):
        """Test creating a FeedbackEntry."""
        entry = FeedbackEntry(
            feedback_id="feedback_abc123",
            workflow_name="code-review",
            stage_name="analysis",
            tier="cheap",
            quality_score=0.85,
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            metadata={"tokens": 150, "latency_ms": 1200},
        )

        assert entry.feedback_id == "feedback_abc123"
        assert entry.workflow_name == "code-review"
        assert entry.stage_name == "analysis"
        assert entry.tier == "cheap"
        assert entry.quality_score == 0.85
        assert entry.metadata["tokens"] == 150

    def test_to_dict(self):
        """Test converting FeedbackEntry to dict."""
        entry = FeedbackEntry(
            feedback_id="feedback_abc123",
            workflow_name="code-review",
            stage_name="analysis",
            tier="cheap",
            quality_score=0.85,
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            metadata={"tokens": 150},
        )

        entry_dict = entry.to_dict()

        assert entry_dict["feedback_id"] == "feedback_abc123"
        assert entry_dict["workflow_name"] == "code-review"
        assert entry_dict["quality_score"] == 0.85
        assert entry_dict["timestamp"] == "2026-01-27T12:00:00"

    def test_from_dict(self):
        """Test creating FeedbackEntry from dict."""
        data = {
            "feedback_id": "feedback_xyz789",
            "workflow_name": "test-generation",
            "stage_name": "analysis",
            "tier": "capable",
            "quality_score": 0.92,
            "timestamp": "2026-01-27T12:00:00",
            "metadata": {"tokens": 250},
        }

        entry = FeedbackEntry.from_dict(data)

        assert entry.feedback_id == "feedback_xyz789"
        assert entry.workflow_name == "test-generation"
        assert entry.quality_score == 0.92


class TestQualityStats:
    """Test QualityStats dataclass."""

    def test_quality_stats_creation(self):
        """Test creating QualityStats."""
        stats = QualityStats(
            workflow_name="code-review",
            stage_name="analysis",
            tier="cheap",
            avg_quality=0.82,
            min_quality=0.65,
            max_quality=0.95,
            sample_count=25,
            recent_trend=0.15,
        )

        assert stats.workflow_name == "code-review"
        assert stats.avg_quality == 0.82
        assert stats.sample_count == 25
        assert stats.recent_trend == 0.15


class TestTierRecommendation:
    """Test TierRecommendation dataclass."""

    def test_tier_recommendation_creation(self):
        """Test creating TierRecommendation."""
        recommendation = TierRecommendation(
            current_tier="cheap",
            recommended_tier="capable",
            confidence=0.85,
            reason="Low quality (0.62) - upgrade for better results",
            stats={
                "cheap": QualityStats(
                    workflow_name="test",
                    stage_name="analysis",
                    tier="cheap",
                    avg_quality=0.62,
                    min_quality=0.50,
                    max_quality=0.75,
                    sample_count=15,
                    recent_trend=-0.1,
                ),
            },
        )

        assert recommendation.current_tier == "cheap"
        assert recommendation.recommended_tier == "capable"
        assert recommendation.confidence == 0.85
        assert "upgrade" in recommendation.reason


class TestFeedbackLoop:
    """Test FeedbackLoop class."""

    def test_init_without_memory_uses_in_memory_store(self):
        """Test FeedbackLoop falls back to _InMemoryStore when no backend given."""
        from attune.telemetry.feedback_loop import _InMemoryStore

        loop = FeedbackLoop()

        assert loop.memory is not None
        assert isinstance(loop.memory, _InMemoryStore)
        assert loop.memory.is_connected()

    def test_init_with_memory(self):
        """Test FeedbackLoop initialization with explicit memory backend."""
        mock_memory = Mock()
        loop = FeedbackLoop(memory=mock_memory)

        assert loop.memory == mock_memory

    def test_record_feedback_with_in_memory_store(self):
        """Test record_feedback works with the default in-memory store."""
        loop = FeedbackLoop()

        feedback_id = loop.record_feedback(
            workflow_name="test",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
            quality_score=0.85,
        )

        assert feedback_id.startswith("feedback_")

    def test_record_feedback_validates_quality_score(self):
        """Test record_feedback validates quality score range."""
        loop = FeedbackLoop()

        assert loop.record_feedback("test", "analysis", "cheap", 1.5) == ""
        assert loop.record_feedback("test", "analysis", "cheap", -0.1) == ""

    def test_record_feedback_stores_entry(self):
        """Test that record_feedback stores feedback retrievable via history."""
        loop = FeedbackLoop()

        feedback_id = loop.record_feedback(
            workflow_name="code-review",
            stage_name="analysis",
            tier=ModelTier.CHEAP,
            quality_score=0.85,
            metadata={"tokens": 150},
        )

        assert feedback_id.startswith("feedback_")

        history = loop.get_feedback_history("code-review", "analysis")
        assert len(history) == 1
        assert history[0].feedback_id == feedback_id
        assert history[0].quality_score == 0.85

    def test_record_feedback_converts_model_tier_enum(self):
        """Test that record_feedback converts ModelTier enum to string."""
        loop = FeedbackLoop()

        feedback_id = loop.record_feedback(
            workflow_name="test",
            stage_name="analysis",
            tier=ModelTier.CAPABLE,
            quality_score=0.88,
        )

        assert feedback_id != ""
        keys = loop.memory.keys("feedback:test:analysis:capable:*")
        assert len(keys) == 1
        assert "capable" in keys[0]

    def test_get_feedback_history_empty(self):
        """Test get_feedback_history returns empty list when no data."""
        loop = FeedbackLoop()

        history = loop.get_feedback_history("test-workflow", "analysis")

        assert history == []

    def test_get_feedback_history_filters_by_tier(self):
        """Test get_feedback_history filters results by tier."""
        loop = FeedbackLoop()

        loop.record_feedback("test", "analysis", "cheap", 0.75)
        loop.record_feedback("test", "analysis", "capable", 0.88)

        history = loop.get_feedback_history("test", "analysis", tier="cheap")

        assert len(history) == 1
        assert history[0].tier == "cheap"

    def test_get_quality_stats_no_data(self):
        """Test get_quality_stats returns None when no data."""
        loop = FeedbackLoop()

        stats = loop.get_quality_stats("test", "analysis")

        assert stats is None

    def test_get_quality_stats_calculates_correctly(self):
        """Test get_quality_stats calculates statistics correctly."""
        loop = FeedbackLoop()

        # Average: (0.5+0.6+0.7+0.8+0.9 + 0.6+0.7+0.8+0.9+1.0) / 10 = 0.75
        for score in [0.5, 0.6, 0.7, 0.8, 0.9, 0.6, 0.7, 0.8, 0.9, 1.0]:
            loop.record_feedback("test", "analysis", "cheap", score)

        stats = loop.get_quality_stats("test", "analysis", tier="cheap")

        assert stats is not None
        assert stats.sample_count == 10
        assert stats.min_quality == 0.5
        assert stats.max_quality == 1.0
        assert abs(stats.avg_quality - 0.75) < 0.01

    def test_recommend_tier_no_data(self):
        """Test recommend_tier with no feedback data."""
        loop = FeedbackLoop()

        recommendation = loop.recommend_tier("test", "analysis", current_tier="cheap")

        assert recommendation.current_tier == "cheap"
        assert recommendation.recommended_tier == "cheap"
        assert recommendation.confidence == 0.0
        assert "No feedback data" in recommendation.reason

    def test_recommend_tier_insufficient_samples(self):
        """Test recommend_tier with fewer than MIN_SAMPLES entries."""
        loop = FeedbackLoop()

        for _ in range(5):  # MIN_SAMPLES = 10
            loop.record_feedback("test", "analysis", "cheap", 0.8)

        recommendation = loop.recommend_tier("test", "analysis", current_tier="cheap")

        assert recommendation.current_tier == "cheap"
        assert recommendation.recommended_tier == "cheap"
        assert recommendation.confidence == 0.0
        assert "Insufficient data" in recommendation.reason

    def test_recommend_tier_upgrade_on_low_quality(self):
        """Test recommend_tier suggests upgrade when quality is below threshold."""
        loop = FeedbackLoop()

        for _ in range(15):
            loop.record_feedback("test", "analysis", "cheap", 0.6)  # below 0.7

        recommendation = loop.recommend_tier("test", "analysis", current_tier="cheap")

        assert recommendation.current_tier == "cheap"
        assert recommendation.recommended_tier == "capable"
        assert "upgrade" in recommendation.reason.lower()

    def test_recommend_tier_maintain_on_acceptable_quality(self):
        """Test recommend_tier maintains tier when quality is acceptable."""
        loop = FeedbackLoop()

        for _ in range(15):
            loop.record_feedback("test", "analysis", "cheap", 0.8)  # above 0.7, below 0.9

        recommendation = loop.recommend_tier("test", "analysis", current_tier="cheap")

        assert recommendation.current_tier == "cheap"
        assert recommendation.recommended_tier == "cheap"
        assert "maintain" in recommendation.reason.lower()

    def test_recommend_tier_already_premium(self):
        """Test recommend_tier stays on premium even with low quality."""
        loop = FeedbackLoop()

        for _ in range(15):
            loop.record_feedback("test", "analysis", "premium", 0.6)

        recommendation = loop.recommend_tier("test", "analysis", current_tier="premium")

        assert recommendation.current_tier == "premium"
        assert recommendation.recommended_tier == "premium"
        assert "already using premium" in recommendation.reason.lower()

    def test_get_underperforming_stages_no_stages(self):
        """Test get_underperforming_stages returns empty when no data."""
        loop = FeedbackLoop()

        underperforming = loop.get_underperforming_stages("test-workflow")

        assert underperforming == []

    def test_get_underperforming_stages_filters_by_threshold(self):
        """Test get_underperforming_stages returns only stages below threshold."""
        loop = FeedbackLoop()

        # stage1: good quality
        loop.record_feedback("test", "stage1", "cheap", 0.85)
        loop.record_feedback("test", "stage1", "cheap", 0.85)
        # stage2: poor quality
        loop.record_feedback("test", "stage2", "cheap", 0.55)
        loop.record_feedback("test", "stage2", "cheap", 0.55)

        underperforming = loop.get_underperforming_stages("test", quality_threshold=0.7)

        assert len(underperforming) == 1
        assert underperforming[0][0] == "stage2/cheap"
        assert underperforming[0][1].avg_quality < 0.7

    def test_clear_feedback_no_stage(self):
        """Test clear_feedback removes all entries for a workflow."""
        loop = FeedbackLoop()

        loop.record_feedback("test", "stage1", "cheap", 0.8)
        loop.record_feedback("test", "stage2", "cheap", 0.9)

        cleared = loop.clear_feedback("test")

        assert cleared == 2
        assert loop.get_feedback_history("test", "stage1") == []
        assert loop.get_feedback_history("test", "stage2") == []

    def test_clear_feedback_specific_stage(self):
        """Test clear_feedback removes only the specified stage."""
        loop = FeedbackLoop()

        loop.record_feedback("test", "stage1", "cheap", 0.8)
        loop.record_feedback("test", "stage2", "cheap", 0.9)

        cleared = loop.clear_feedback("test", stage_name="stage1")

        assert cleared == 1
        assert loop.get_feedback_history("test", "stage1") == []
        assert len(loop.get_feedback_history("test", "stage2")) == 1


# =============================================================================
# Branch-coverage additions — targets previously-uncovered lines
# =============================================================================


class TestInMemoryStoreBranches:
    """Cover _InMemoryStore expiry, stats, and capabilities (lines 77-116)."""

    def test_retrieve_expired_entry_returns_none(self):
        store = _InMemoryStore()
        # Directly insert an entry that is already expired
        store._data["k"] = ("v", time.monotonic() - 10)
        result = store.retrieve("k")
        assert result is None

    def test_keys_prunes_expired(self):
        store = _InMemoryStore()
        store.stash("old_key", "v", ttl=1)
        # Force the key to appear expired
        key_internal = list(store._data.keys())[0]
        store._data[key_internal] = ("v", time.monotonic() - 10)  # already expired
        with patch("attune.telemetry.feedback_loop.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 100
            result = store.keys("*")
        assert "old_key" not in result

    def test_get_stats_returns_dict(self):
        store = _InMemoryStore()
        stats = store.get_stats()
        assert "entries" in stats
        assert stats["backend"] == "in-memory"

    def test_close_is_noop(self):
        store = _InMemoryStore()
        store.close()  # Should not raise

    def test_supports_realtime_false(self):
        assert _InMemoryStore().supports_realtime() is False

    def test_supports_distributed_false(self):
        assert _InMemoryStore().supports_distributed() is False


class TestFeedbackLoopBranches:
    """Cover remaining branches in FeedbackLoop (lines 161-406)."""

    def test_record_feedback_with_model_tier_enum(self):
        from attune.telemetry.feedback_loop import ModelTier

        loop = FeedbackLoop()
        fid = loop.record_feedback("wf", "stage", ModelTier.CHEAP, 0.9)
        assert fid != ""

    def test_record_feedback_stash_exception_returns_empty(self):
        loop = FeedbackLoop()
        loop.memory.stash = MagicMock(side_effect=RuntimeError("disk full"))
        result = loop.record_feedback("wf", "stage", "cheap", 0.8)
        assert result == ""

    def test_get_feedback_history_with_model_tier_enum(self):
        from attune.telemetry.feedback_loop import ModelTier

        loop = FeedbackLoop()
        loop.record_feedback("wf2", "s2", ModelTier.CAPABLE, 0.75)
        result = loop.get_feedback_history("wf2", "s2", tier=ModelTier.CAPABLE)
        assert isinstance(result, list)

    def test_get_feedback_history_parse_error_continues(self):
        """Bad entry in store is skipped rather than raising."""
        loop = FeedbackLoop()
        loop.memory.stash("feedback:wf:s:cheap:bad1", {"corrupted": True})
        # Patch FeedbackEntry.from_dict to fail on this entry
        with patch(
            "attune.telemetry.feedback_loop.FeedbackEntry.from_dict",
            side_effect=ValueError("parse error"),
        ):
            result = loop.get_feedback_history("wf", "s", tier="cheap")
        assert isinstance(result, list)

    def test_get_feedback_history_memory_exception_returns_empty(self):
        loop = FeedbackLoop()
        loop.memory.keys = MagicMock(side_effect=RuntimeError("redis down"))
        result = loop.get_feedback_history("wf", "stage")
        assert result == []

    def test_retrieve_feedback_exception_returns_none(self):
        loop = FeedbackLoop()
        loop.memory.retrieve = MagicMock(side_effect=RuntimeError("oops"))
        result = loop._retrieve_feedback("some:key")
        assert result is None

    def test_recommend_tier_no_current_tier_inferred_from_history(self):
        """current_tier=None → inferred from first history entry (lines 377-379)."""
        loop = FeedbackLoop()
        # Seed enough data for stats (10+ samples) at 'cheap' tier
        for _ in range(12):
            loop.record_feedback("wf3", "s3", "cheap", 0.5)
        rec = loop.recommend_tier("wf3", "s3", current_tier=None)
        assert rec.current_tier in ("cheap", "capable", "premium", "unknown")

    def test_recommend_tier_capable_low_quality_upgrades_to_premium(self):
        """Low quality on capable tier → recommend premium (lines 403-404)."""
        loop = FeedbackLoop()
        for _ in range(12):
            loop.record_feedback("wf4", "s4", "capable", 0.3)
        rec = loop.recommend_tier("wf4", "s4", current_tier="capable")
        assert rec.recommended_tier == "premium"

    def test_recommend_tier_model_tier_enum(self):
        from attune.telemetry.feedback_loop import ModelTier

        loop = FeedbackLoop()
        for _ in range(12):
            loop.record_feedback("wf5", "s5", "cheap", 0.9)
        rec = loop.recommend_tier("wf5", "s5", current_tier=ModelTier.CHEAP)
        assert rec is not None


class _BatchBackend:
    """MemoryBackend stub whose retrieve_many IS the per-key contract.

    Per the #2162 transport-swap lesson: the batched read is defined in
    terms of the single read, so tests configuring payloads the old way
    keep working, and call counters expose which transport actually ran.
    """

    def __init__(self):
        self._data = {}
        self.retrieve_calls = 0
        self.retrieve_many_calls = 0

    def stash(self, key, value, ttl=None, agent_id=None):
        self._data[key] = value
        return True

    def retrieve(self, key, agent_id=None):
        self.retrieve_calls += 1
        return self._data.get(key)

    def retrieve_many(self, keys, agent_id=None):
        self.retrieve_many_calls += 1
        return {k: self._data.get(k) for k in keys}

    def keys(self, pattern="*"):
        import fnmatch

        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]

    def delete(self, key, agent_id=None):
        return self._data.pop(key, None) is not None


class TestBatchedRetrieval:
    """#2237: history and underperforming-stages read in one batch."""

    def _seed(self, loop, stage, tier, scores):
        for i, score in enumerate(scores):
            loop.record_feedback(
                workflow_name="wf",
                stage_name=stage,
                tier=tier,
                quality_score=score,
                metadata={"seed_index": i},
            )

    def test_history_uses_one_batched_read(self):
        backend = _BatchBackend()
        loop = FeedbackLoop(memory=backend)
        self._seed(loop, "review", "cheap", [0.9, 0.8, 0.7])

        entries = loop.get_feedback_history("wf", "review", tier="cheap")

        assert len(entries) == 3  # payloads were actually read
        assert backend.retrieve_many_calls == 1
        assert backend.retrieve_calls == 0  # no per-key N+1

    def test_history_falls_back_without_retrieve_many(self):
        class _NoBatchBackend(_BatchBackend):
            retrieve_many = None  # not callable -> per-key fallback

        backend = _NoBatchBackend()
        loop = FeedbackLoop(memory=backend)
        self._seed(loop, "review", "cheap", [0.9, 0.8])
        entries = loop.get_feedback_history("wf", "review", tier="cheap")
        assert len(entries) == 2
        assert backend.retrieve_calls == 2  # per-key fallback ran

    def test_underperforming_stages_single_batch_across_combos(self):
        backend = _BatchBackend()
        loop = FeedbackLoop(memory=backend)
        self._seed(loop, "review", "cheap", [0.2, 0.3, 0.25])  # bad
        self._seed(loop, "review", "premium", [0.95, 0.9])  # good
        self._seed(loop, "summarize", "cheap", [0.5, 0.4])  # bad

        under = loop.get_underperforming_stages("wf", quality_threshold=0.7)

        labels = [label for label, _ in under]
        # Both bad combos flagged, worst first; the good combo absent.
        assert labels[0] == "review/cheap"
        assert "summarize/cheap" in labels
        assert "review/premium" not in labels
        # The stats are real (computed from actually-read payloads).
        by_label = dict(under)
        assert by_label["review/cheap"].sample_count == 3
        # ONE batched read served every combo — not one scan+N per combo.
        assert backend.retrieve_many_calls == 1
        assert backend.retrieve_calls == 0

    def test_malformed_record_skipped_others_kept(self):
        backend = _BatchBackend()
        loop = FeedbackLoop(memory=backend)
        self._seed(loop, "review", "cheap", [0.9, 0.8])
        # Corrupt one stored record: from_dict will raise on it.
        bad_key = next(iter(backend._data))
        backend._data[bad_key] = {"not": "a feedback entry"}

        entries = loop.get_feedback_history("wf", "review", tier="cheap")
        assert len(entries) == 1
