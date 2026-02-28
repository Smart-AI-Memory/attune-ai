"""Tests for PatternLearner - Phase 3: Learning Grammar.

Tests cover:
- Execution record creation and tracking
- Pattern statistics aggregation
- Context similarity matching
- Hybrid recommendation engine
- Memory + file persistence
"""

from unittest.mock import patch

import pytest

from attune.orchestration.pattern_learner import (
    ContextSignature,
    ExecutionRecord,
    LearningStore,
    PatternLearner,
    PatternRecommender,
    PatternStats,
    get_learner,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_storage(tmp_path):
    """Create a temporary storage file path."""
    return str(tmp_path / "test_learning.json")


@pytest.fixture
def learner(temp_storage):
    """Create a learner with temporary storage."""
    return PatternLearner(storage_path=temp_storage)


@pytest.fixture
def populated_store(temp_storage):
    """Create a store with sample data."""
    store = LearningStore(temp_storage)

    # Add diverse records
    records = [
        ExecutionRecord(
            pattern="sequential",
            success=True,
            duration_seconds=2.0,
            cost=0.05,
            confidence=0.9,
            context_features={"task_type": "code_review", "agent_count": 2},
        ),
        ExecutionRecord(
            pattern="sequential",
            success=True,
            duration_seconds=2.5,
            cost=0.06,
            confidence=0.85,
            context_features={"task_type": "code_review", "agent_count": 3},
        ),
        ExecutionRecord(
            pattern="parallel",
            success=True,
            duration_seconds=1.5,
            cost=0.08,
            confidence=0.8,
            context_features={"task_type": "test_gen", "agent_count": 4},
        ),
        ExecutionRecord(
            pattern="parallel",
            success=False,
            duration_seconds=3.0,
            cost=0.10,
            confidence=0.4,
            context_features={"task_type": "test_gen", "agent_count": 2},
        ),
        ExecutionRecord(
            pattern="conditional",
            success=True,
            duration_seconds=4.0,
            cost=0.15,
            confidence=0.95,
            context_features={"task_type": "code_review", "has_conditions": True},
        ),
    ]

    for record in records:
        store.add_record(record)

    store.save()
    return store


# =============================================================================
# ExecutionRecord Tests
# =============================================================================


class TestExecutionRecord:
    """Tests for ExecutionRecord dataclass."""

    def test_create_record(self):
        """Test creating an execution record."""
        record = ExecutionRecord(
            pattern="sequential",
            success=True,
            duration_seconds=2.5,
            cost=0.05,
            confidence=0.9,
        )
        assert record.pattern == "sequential"
        assert record.success is True
        assert record.duration_seconds == 2.5
        assert record.timestamp  # Should be auto-generated

    def test_to_dict(self):
        """Test serialization to dict."""
        record = ExecutionRecord(
            pattern="parallel",
            success=False,
            duration_seconds=1.0,
        )
        data = record.to_dict()

        assert data["pattern"] == "parallel"
        assert data["success"] is False
        assert "timestamp" in data

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "pattern": "debate",
            "success": True,
            "duration_seconds": 3.0,
            "cost": 0.1,
            "confidence": 0.8,
            "context_features": {"task": "review"},
            "timestamp": "2026-01-01T00:00:00",
        }
        record = ExecutionRecord.from_dict(data)

        assert record.pattern == "debate"
        assert record.confidence == 0.8
        assert record.context_features["task"] == "review"


# =============================================================================
# PatternStats Tests
# =============================================================================


class TestPatternStats:
    """Tests for PatternStats aggregation."""

    def test_initial_state(self):
        """Test initial stats state."""
        stats = PatternStats(pattern="sequential")
        assert stats.total_executions == 0
        assert stats.success_rate == 0.0

    def test_update_success(self):
        """Test updating with successful execution."""
        stats = PatternStats(pattern="sequential")
        record = ExecutionRecord(
            pattern="sequential",
            success=True,
            duration_seconds=2.0,
            cost=0.05,
            confidence=0.9,
        )

        stats.update(record)

        assert stats.total_executions == 1
        assert stats.success_count == 1
        assert stats.success_rate == 1.0
        assert stats.avg_duration == 2.0

    def test_update_failure(self):
        """Test updating with failed execution."""
        stats = PatternStats(pattern="sequential")
        record = ExecutionRecord(
            pattern="sequential",
            success=False,
            duration_seconds=5.0,
        )

        stats.update(record)

        assert stats.total_executions == 1
        assert stats.success_count == 0
        assert stats.success_rate == 0.0

    def test_multiple_updates(self):
        """Test aggregation across multiple updates."""
        stats = PatternStats(pattern="parallel")

        # 3 successes, 1 failure
        for success in [True, True, False, True]:
            record = ExecutionRecord(
                pattern="parallel",
                success=success,
                duration_seconds=2.0,
                cost=0.05,
            )
            stats.update(record)

        assert stats.total_executions == 4
        assert stats.success_count == 3
        assert stats.success_rate == 0.75
        assert stats.avg_duration == 2.0

    def test_to_dict_includes_computed(self):
        """Test that to_dict includes computed properties."""
        stats = PatternStats(pattern="test")
        stats.total_executions = 10
        stats.success_count = 8
        stats.total_duration = 20.0

        data = stats.to_dict()

        assert data["success_rate"] == 0.8
        assert data["avg_duration"] == 2.0


# =============================================================================
# ContextSignature Tests
# =============================================================================


class TestContextSignature:
    """Tests for ContextSignature similarity matching."""

    def test_from_context(self):
        """Test extracting signature from context."""
        context = {
            "task_type": "code_review",
            "agents": [1, 2, 3],
            "_conditional": {"branch": "then"},
            "priority": "high",
        }

        sig = ContextSignature.from_context(context)

        assert sig.task_type == "code_review"
        assert sig.agent_count == 3
        assert sig.has_conditions is True
        assert sig.priority == "high"

    def test_identical_similarity(self):
        """Test that identical signatures have similarity 1.0."""
        sig1 = ContextSignature(
            task_type="code_review",
            agent_count=2,
            has_conditions=True,
            priority="high",
        )
        sig2 = ContextSignature(
            task_type="code_review",
            agent_count=2,
            has_conditions=True,
            priority="high",
        )

        assert sig1.similarity(sig2) == 1.0

    def test_different_task_types(self):
        """Test similarity with different task types."""
        sig1 = ContextSignature(task_type="code_review")
        sig2 = ContextSignature(task_type="test_gen")

        # Should be low but not zero due to other defaults matching
        similarity = sig1.similarity(sig2)
        assert 0 < similarity < 1.0

    def test_partial_task_match(self):
        """Test partial matching on task type prefix."""
        sig1 = ContextSignature(task_type="code_review")
        sig2 = ContextSignature(task_type="code_analysis")

        # Should get partial credit for matching prefix
        similarity = sig1.similarity(sig2)
        assert similarity > 0.5  # Better than random

    def test_agent_count_similarity(self):
        """Test agent count affects similarity."""
        sig1 = ContextSignature(task_type="test", agent_count=4)
        sig2 = ContextSignature(task_type="test", agent_count=2)
        sig3 = ContextSignature(task_type="test", agent_count=4)

        # Same count should be more similar
        assert sig1.similarity(sig3) > sig1.similarity(sig2)


# =============================================================================
# LearningStore Tests
# =============================================================================


class TestLearningStore:
    """Tests for LearningStore persistence."""

    def test_add_and_retrieve(self, temp_storage):
        """Test adding records and retrieving stats."""
        store = LearningStore(temp_storage)

        record = ExecutionRecord(
            pattern="sequential",
            success=True,
            duration_seconds=2.0,
        )
        store.add_record(record)

        stats = store.get_stats("sequential")
        assert stats is not None
        assert stats.total_executions == 1

    def test_persistence(self, temp_storage):
        """Test that data persists across instances."""
        # First instance - add data
        store1 = LearningStore(temp_storage)
        store1.add_record(ExecutionRecord(pattern="parallel", success=True, duration_seconds=1.0))
        store1.save()

        # Second instance - should load data
        store2 = LearningStore(temp_storage)
        stats = store2.get_stats("parallel")

        assert stats is not None
        assert stats.total_executions == 1

    def test_get_all_stats_sorted(self, populated_store):
        """Test that get_all_stats returns sorted by success rate."""
        all_stats = populated_store.get_all_stats()

        # Should be sorted by success rate (descending)
        rates = [s.success_rate for s in all_stats]
        assert rates == sorted(rates, reverse=True)

    def test_find_similar_records(self, populated_store):
        """Test finding records with similar context."""
        signature = ContextSignature(
            task_type="code_review",
            agent_count=2,
        )

        similar = populated_store.find_similar_records(signature, limit=5)

        # Should find code_review records
        assert len(similar) > 0
        patterns = [r.pattern for r, _ in similar]
        assert "sequential" in patterns or "conditional" in patterns


# =============================================================================
# PatternRecommender Tests
# =============================================================================


class TestPatternRecommender:
    """Tests for hybrid recommendation engine."""

    def test_recommend_from_similar(self, populated_store):
        """Test recommendations based on similar contexts."""
        recommender = PatternRecommender(populated_store)

        context = {"task_type": "code_review", "agents": [1, 2]}
        recommendations = recommender.recommend(context, top_k=3)

        assert len(recommendations) > 0
        # Sequential had 100% success for code_review
        patterns = [r.pattern for r in recommendations]
        assert "sequential" in patterns

    def test_statistical_fallback(self, temp_storage):
        """Test statistical fallback when no similar contexts."""
        store = LearningStore(temp_storage)

        # Add records without context features
        for _i in range(5):
            store.add_record(
                ExecutionRecord(
                    pattern="parallel",
                    success=True,
                    duration_seconds=1.0,
                ),
            )

        recommender = PatternRecommender(store)
        recommendations = recommender.recommend(
            {"task_type": "completely_new_task"},
            top_k=3,
        )

        # Should still get recommendations based on stats
        assert len(recommendations) > 0

    def test_recommendation_contains_metrics(self, populated_store):
        """Test that recommendations include expected metrics."""
        recommender = PatternRecommender(populated_store)

        recommendations = recommender.recommend(
            {"task_type": "code_review"},
            top_k=1,
        )

        if recommendations:
            rec = recommendations[0]
            assert rec.pattern
            assert 0 <= rec.confidence <= 1
            assert rec.reason
            assert rec.expected_success_rate >= 0


# =============================================================================
# PatternLearner Tests
# =============================================================================


class TestPatternLearner:
    """Tests for main PatternLearner interface."""

    def test_record_and_recommend(self, learner):
        """Test full workflow: record then recommend."""
        # Record some executions
        learner.record(
            pattern="sequential",
            success=True,
            duration=2.0,
            context={"task_type": "review"},
        )
        learner.record(
            pattern="parallel",
            success=False,
            duration=3.0,
            context={"task_type": "review"},
        )

        # Get recommendations
        recommendations = learner.recommend({"task_type": "review"})

        # Sequential should be recommended (100% success vs 0%)
        if recommendations:
            assert recommendations[0].pattern == "sequential"

    def test_get_stats(self, learner):
        """Test getting stats for specific pattern."""
        learner.record(pattern="debate", success=True, duration=5.0)
        learner.record(pattern="debate", success=True, duration=4.0)
        learner.record(pattern="debate", success=False, duration=6.0)

        stats = learner.get_stats("debate")

        assert stats is not None
        assert stats.total_executions == 3
        assert stats.success_rate == pytest.approx(0.667, rel=0.01)

    def test_report(self, learner):
        """Test generating a report."""
        learner.record(pattern="sequential", success=True, duration=1.0)

        report = learner.report()

        assert "Pattern Learning Report" in report
        assert "sequential" in report

    def test_empty_report(self, learner):
        """Test report with no data."""
        report = learner.report()
        assert "No learning data" in report

    def test_save_and_load(self, temp_storage):
        """Test explicit save and reload."""
        # Create and populate
        learner1 = PatternLearner(storage_path=temp_storage)
        learner1.record(pattern="adaptive", success=True, duration=2.0)
        learner1.save()

        # Reload
        learner2 = PatternLearner(storage_path=temp_storage)
        stats = learner2.get_stats("adaptive")

        assert stats is not None
        assert stats.total_executions == 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestLearnerIntegration:
    """Integration tests for complete learning workflow."""

    def test_learning_improves_recommendations(self, temp_storage):
        """Test that learning leads to better recommendations."""
        learner = PatternLearner(storage_path=temp_storage)

        # Phase 1: No data - should get empty/generic recommendations
        learner.recommend({"task_type": "security_scan"})

        # Phase 2: Record successful patterns
        for _ in range(5):
            learner.record(
                pattern="parallel",
                success=True,
                duration=1.5,
                confidence=0.9,
                context={"task_type": "security_scan"},
            )

        # Record a less successful pattern
        for _ in range(3):
            learner.record(
                pattern="sequential",
                success=False,
                duration=5.0,
                confidence=0.3,
                context={"task_type": "security_scan"},
            )

        # Phase 3: Should now recommend parallel
        learned_recs = learner.recommend({"task_type": "security_scan"})

        assert len(learned_recs) > 0
        assert learned_recs[0].pattern == "parallel"
        assert learned_recs[0].confidence > 0.5

    def test_singleton_access(self):
        """Test get_learner returns same instance."""
        with patch("attune.orchestration.pattern_learner._default_learner", None):
            learner1 = get_learner()
            learner2 = get_learner()
            assert learner1 is learner2
