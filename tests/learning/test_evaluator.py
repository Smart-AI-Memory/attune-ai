"""Tests for the session evaluator."""

import pytest

from attune.learning.evaluator import (
    EvaluationResult,
    SessionEvaluator,
    SessionMetrics,
    SessionQuality,
)
from attune.llm.state import CollaborationState


class TestSessionMetrics:
    """Tests for SessionMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metric values."""
        metrics = SessionMetrics()

        assert metrics.interaction_count == 0
        assert metrics.user_corrections == 0
        assert metrics.trust_delta == 0.0

    def test_metrics_to_dict(self):
        """Test converting metrics to dict."""
        metrics = SessionMetrics(
            interaction_count=10,
            user_corrections=2,
            successful_resolutions=3,
        )

        result = metrics.to_dict()

        assert result["interaction_count"] == 10
        assert result["user_corrections"] == 2
        assert result["successful_resolutions"] == 3


class TestEvaluationResult:
    """Tests for EvaluationResult dataclass."""

    def test_create_result(self):
        """Test creating evaluation result."""
        metrics = SessionMetrics(interaction_count=5)
        result = EvaluationResult(
            quality=SessionQuality.GOOD,
            score=0.6,
            metrics=metrics,
            learnable_topics=["error_resolution"],
            recommended_extraction=True,
            reasoning="Test reasoning",
        )

        assert result.quality == SessionQuality.GOOD
        assert result.score == 0.6
        assert result.recommended_extraction is True

    def test_result_to_dict(self):
        """Test converting result to dict."""
        metrics = SessionMetrics()
        result = EvaluationResult(
            quality=SessionQuality.EXCELLENT,
            score=0.8,
            metrics=metrics,
            learnable_topics=["preferences"],
        )

        data = result.to_dict()

        assert data["quality"] == "excellent"
        assert data["score"] == 0.8


class TestSessionEvaluator:
    """Tests for SessionEvaluator class."""

    def test_init_default(self):
        """Test default initialization."""
        evaluator = SessionEvaluator()

        assert evaluator._min_interactions == 3
        assert evaluator._min_score_for_extraction == 0.4

    def test_init_custom(self):
        """Test custom initialization."""
        evaluator = SessionEvaluator(
            min_interactions=5,
            min_score_for_extraction=0.6,
        )

        assert evaluator._min_interactions == 5
        assert evaluator._min_score_for_extraction == 0.6

    def test_evaluate_empty_session(self):
        """Test evaluating empty session."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        result = evaluator.evaluate(state)

        assert result.quality == SessionQuality.SKIP
        assert result.score < 0.1
        assert result.recommended_extraction is False

    def test_evaluate_session_with_corrections(self):
        """Test evaluating session with user corrections."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        # Add interactions with corrections
        state.add_interaction("user", "Help me with async functions", 2)
        state.add_interaction("assistant", "Here's how to use callbacks...", 2)
        state.add_interaction("user", "Actually, I meant async/await syntax", 2)
        state.add_interaction("assistant", "Let me explain async/await...", 3)
        state.add_interaction("user", "That works, thanks!", 2)

        result = evaluator.evaluate(state)

        assert result.metrics.user_corrections >= 1
        assert "user_corrections" in result.learnable_topics
        assert result.score > 0.2

    def test_evaluate_session_with_errors(self):
        """Test evaluating session with error resolution."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        state.add_interaction("user", "I'm getting an error: TypeError", 2)
        state.add_interaction("assistant", "Try adding a null check...", 3)
        state.add_interaction("user", "That works perfectly, thanks!", 2)

        result = evaluator.evaluate(state)

        assert result.metrics.error_mentions >= 1
        assert result.metrics.successful_resolutions >= 1
        assert "error_resolution" in result.learnable_topics

    def test_evaluate_session_with_workarounds(self):
        """Test evaluating session with workarounds."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        state.add_interaction("user", "This library doesn't support X", 2)
        state.add_interaction(
            "assistant",
            "Here's a workaround: use alternative approach Y instead",
            3,
        )
        state.add_interaction("user", "That's a nice hack, it works!", 2)

        result = evaluator.evaluate(state)

        assert result.metrics.workaround_mentions >= 1
        assert "workarounds" in result.learnable_topics

    def test_evaluate_session_with_preferences(self):
        """Test evaluating session with preference signals."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        state.add_interaction("user", "I prefer detailed explanations", 2)
        state.add_interaction("user", "I always use TypeScript for new projects", 2)
        state.add_interaction("assistant", "I'll provide detailed TypeScript examples", 3)

        result = evaluator.evaluate(state)

        assert result.metrics.preference_signals >= 2
        assert "preferences" in result.learnable_topics

    def test_evaluate_trust_improvement(self):
        """Test that trust improvement affects score."""
        evaluator = SessionEvaluator()
        state = CollaborationState(user_id="test_user")

        # Simulate trust improvement
        state.trust_level = 0.8
        state.trust_trajectory = [0.5, 0.6, 0.7, 0.8]

        state.add_interaction("user", "Help me debug this", 2)
        state.add_interaction("assistant", "Here's the fix...", 3)
        state.add_interaction("user", "Perfect, thanks!", 2)

        result = evaluator.evaluate(state)

        # Trust improved from 0.5 to 0.8
        assert result.metrics.trust_delta == pytest.approx(0.3, rel=0.1)
        assert result.score > 0.1  # Trust bonus applied

    def test_should_extract_patterns(self):
        """Test quick extraction check."""
        evaluator = SessionEvaluator(min_score_for_extraction=0.3)
        state = CollaborationState(user_id="test_user")

        # Low value session
        state.add_interaction("user", "Hello", 1)

        assert evaluator.should_extract_patterns(state) is False

        # Add valuable content
        state.add_interaction("user", "Actually, I meant something else", 2)
        state.add_interaction("assistant", "Let me clarify...", 3)
        state.add_interaction("user", "Perfect, that works!", 2)

        # Now should recommend extraction
        assert evaluator.should_extract_patterns(state) is True

    def test_get_extraction_priority(self):
        """Test extraction priority calculation."""
        evaluator = SessionEvaluator()

        # Low priority session
        low_state = CollaborationState(user_id="low")
        low_state.add_interaction("user", "Hello", 1)

        low_priority = evaluator.get_extraction_priority(low_state)

        # High priority session
        high_state = CollaborationState(user_id="high")
        high_state.add_interaction("user", "Error: something failed", 2)
        high_state.add_interaction("assistant", "Here's the fix...", 3)
        high_state.add_interaction("user", "Actually, I meant async", 2)
        high_state.add_interaction("assistant", "For async, try this...", 3)
        high_state.add_interaction("user", "That works perfectly!", 2)

        high_priority = evaluator.get_extraction_priority(high_state)

        assert high_priority > low_priority

    def test_score_to_quality_thresholds(self):
        """Test quality rating thresholds."""
        evaluator = SessionEvaluator()

        assert evaluator._score_to_quality(0.8) == SessionQuality.EXCELLENT
        assert evaluator._score_to_quality(0.6) == SessionQuality.GOOD
        assert evaluator._score_to_quality(0.4) == SessionQuality.AVERAGE
        assert evaluator._score_to_quality(0.15) == SessionQuality.POOR
        assert evaluator._score_to_quality(0.05) == SessionQuality.SKIP
