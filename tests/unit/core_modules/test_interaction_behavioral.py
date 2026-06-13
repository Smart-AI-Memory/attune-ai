"""Behavioral tests for InteractionMixin.

The mixin expects a host class to supply user_id, target_level, logger,
current_empathy_level, and collaboration_state. A minimal _Host provides
those so the mixin's state, interaction, trust, and helper logic can be
exercised in isolation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from attune.core import CollaborationState
from attune.core_modules.interaction import InteractionMixin


class _Host(InteractionMixin):
    """Minimal host satisfying the mixin's expected attributes."""

    def __init__(self, target_level: int = 5, trust: float = 0.5):
        self.user_id = "dev_123"
        self.target_level = target_level
        self.logger = MagicMock()
        self.current_empathy_level = 1
        self.collaboration_state = CollaborationState()
        self.collaboration_state.trust_level = trust


# ---------------------------------------------------------------------------
# get / reset collaboration state
# ---------------------------------------------------------------------------


class TestCollaborationState:
    def test_get_state_zero_interactions_success_rate_zero(self):
        """With no interactions, success_rate guards against divide-by-zero."""
        host = _Host(target_level=4, trust=0.6)
        state = host.get_collaboration_state()

        assert state["success_rate"] == 0
        assert state["trust_level"] == 0.6
        assert state["target_empathy_level"] == 4

    def test_get_state_computes_success_rate(self):
        """success_rate is successful / total when interactions exist."""
        host = _Host()
        host.collaboration_state.total_interactions = 4
        host.collaboration_state.successful_interventions = 3

        assert host.get_collaboration_state()["success_rate"] == 0.75

    def test_reset_state_replaces_with_fresh(self):
        """reset_collaboration_state installs a brand-new state object."""
        host = _Host(trust=0.9)
        host.collaboration_state.total_interactions = 7
        host.reset_collaboration_state()

        assert host.collaboration_state.total_interactions == 0
        assert isinstance(host.collaboration_state, CollaborationState)


# ---------------------------------------------------------------------------
# interact
# ---------------------------------------------------------------------------


class TestInteract:
    def test_interact_low_trust_no_predictions(self):
        """Low trust yields a low level with no predictions; tracking updates."""
        host = _Host(target_level=5, trust=0.4)  # -> level 2
        response = host.interact("dev_123", "How do I optimize?")

        assert response.level == 2
        assert response.predictions is None
        assert host.collaboration_state.total_interactions == 1
        assert host.current_empathy_level == 2

    def test_interact_high_trust_generates_predictions(self):
        """High trust + high target level reaches L4+, producing predictions."""
        host = _Host(target_level=5, trust=0.9)  # -> level 5
        response = host.interact("dev_123", "Optimize this", context={"domain": "db"})

        assert response.level == 5
        assert response.predictions is not None
        assert response.predictions  # non-empty list
        assert 0.0 <= response.confidence <= 1.0


# ---------------------------------------------------------------------------
# record_success
# ---------------------------------------------------------------------------


class TestRecordSuccess:
    def test_record_success_true_updates_trust_and_logs(self):
        host = _Host()
        host.collaboration_state.update_trust = MagicMock()

        host.record_success(success=True)

        host.collaboration_state.update_trust.assert_called_once_with("success")
        host.logger.debug.assert_called_once()

    def test_record_success_false_records_failure(self):
        host = _Host()
        host.collaboration_state.update_trust = MagicMock()

        host.record_success(success=False)

        host.collaboration_state.update_trust.assert_called_once_with("failure")


# ---------------------------------------------------------------------------
# helper methods
# ---------------------------------------------------------------------------


class TestHelpers:
    @pytest.mark.parametrize(
        ("trust", "target", "expected"),
        [
            (0.2, 5, 1),  # reactive
            (0.4, 5, 2),  # guided
            (0.6, 5, 3),  # proactive
            (0.6, 2, 2),  # proactive capped by target
            (0.8, 5, 4),  # anticipatory
            (0.9, 5, 5),  # systems
            (0.9, 3, 3),  # systems capped by target
        ],
    )
    def test_determine_interaction_level(self, trust, target, expected):
        host = _Host(target_level=target)
        assert host._determine_interaction_level(trust, {}) == expected

    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
    def test_generate_response_known_levels(self, level):
        host = _Host()
        out = host._generate_response("hi", {}, level)
        assert f"[Level {level}]" in out
        assert "hi" in out

    def test_generate_response_unknown_level_fallback(self):
        host = _Host()
        out = host._generate_response("hi", {}, 99)
        assert "Response" in out

    def test_generate_predictions_returns_list(self):
        host = _Host()
        preds = host._generate_predictions("hi", {})
        assert isinstance(preds, list)
        assert preds

    def test_calculate_confidence_with_context(self):
        """Confidence blends context completeness with trust."""
        host = _Host()
        conf = host._calculate_confidence({"a": 1, "b": 2}, trust=0.8)
        # context_score = min(1.0, 2 * 0.1) = 0.2 -> (0.2 + 0.8) / 2 = 0.5
        assert conf == pytest.approx(0.5)

    def test_calculate_confidence_empty_context_uses_default(self):
        """Empty context falls back to a 0.5 context score."""
        host = _Host()
        conf = host._calculate_confidence({}, trust=0.5)
        # context_score = 0.5 -> (0.5 + 0.5) / 2 = 0.5
        assert conf == pytest.approx(0.5)
