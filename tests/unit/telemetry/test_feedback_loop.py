"""Unit tests for Feedback Loop (Pattern 6).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from unittest.mock import Mock

from attune.telemetry.feedback_loop import (
    FeedbackEntry,
    FeedbackLoop,
    ModelTier,
    QualityStats,
    TierRecommendation,
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
                )
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
