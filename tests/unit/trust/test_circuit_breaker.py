"""Tests for Trust Circuit Breaker

Tests comprehensive trust management functionality including:
- TrustState enum and state transitions
- TrustDamageType and damage events
- TrustConfig configuration
- TrustCircuitBreaker state machine
- Damage recording and recovery
- Serialization/deserialization
- Factory function

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from attune.trust.circuit_breaker import (
    TrustCircuitBreaker,
    TrustConfig,
    TrustDamageEvent,
    TrustDamageType,
    TrustRecoveryEvent,
    TrustState,
    create_trust_breaker,
)

# =========================================================================
# Test TrustState Enum
# =========================================================================


class TestTrustState:
    """Tests for TrustState enum."""

    def test_state_values(self):
        """Test state enum has expected values."""
        assert TrustState.FULL_AUTONOMY.value == "full_autonomy"
        assert TrustState.REDUCED_AUTONOMY.value == "reduced_autonomy"
        assert TrustState.SUPERVISED.value == "supervised"

    def test_state_count(self):
        """Test there are exactly 3 states."""
        assert len(TrustState) == 3


# =========================================================================
# Test TrustDamageType Enum
# =========================================================================


class TestTrustDamageType:
    """Tests for TrustDamageType enum."""

    def test_damage_type_values(self):
        """Test damage type enum has expected values."""
        assert TrustDamageType.WRONG_ANSWER.value == "wrong_answer"
        assert TrustDamageType.IGNORED_PREFERENCE.value == "ignored_preference"
        assert TrustDamageType.UNEXPECTED_ACTION.value == "unexpected_action"
        assert TrustDamageType.SLOW_RESPONSE.value == "slow_response"
        assert TrustDamageType.MISUNDERSTOOD_INTENT.value == "misunderstood_intent"
        assert TrustDamageType.REPETITIVE_ERROR.value == "repetitive_error"

    def test_damage_type_count(self):
        """Test there are exactly 6 damage types."""
        assert len(TrustDamageType) == 6


# =========================================================================
# Test TrustDamageEvent
# =========================================================================


class TestTrustDamageEvent:
    """Tests for TrustDamageEvent dataclass."""

    def test_create_event(self):
        """Test creating a damage event."""
        event = TrustDamageEvent(
            event_type=TrustDamageType.WRONG_ANSWER,
            context="Provided incorrect API documentation",
            severity=0.8,
            user_explicit=True,
        )

        assert event.event_type == TrustDamageType.WRONG_ANSWER
        assert event.context == "Provided incorrect API documentation"
        assert event.severity == 0.8
        assert event.user_explicit is True
        assert isinstance(event.timestamp, datetime)

    def test_create_event_defaults(self):
        """Test damage event with default values."""
        event = TrustDamageEvent(event_type=TrustDamageType.SLOW_RESPONSE)

        assert event.event_type == TrustDamageType.SLOW_RESPONSE
        assert event.context == ""
        assert event.severity == 1.0
        assert event.user_explicit is False

    def test_event_type_from_string(self):
        """Test event_type can be passed as string."""
        event = TrustDamageEvent(event_type="wrong_answer")  # type: ignore

        assert event.event_type == TrustDamageType.WRONG_ANSWER


# =========================================================================
# Test TrustRecoveryEvent
# =========================================================================


class TestTrustRecoveryEvent:
    """Tests for TrustRecoveryEvent dataclass."""

    def test_create_event(self):
        """Test creating a recovery event."""
        event = TrustRecoveryEvent(
            context="User praised code review quality",
            user_explicit=True,
        )

        assert event.context == "User praised code review quality"
        assert event.user_explicit is True
        assert isinstance(event.timestamp, datetime)

    def test_create_event_defaults(self):
        """Test recovery event with default values."""
        event = TrustRecoveryEvent()

        assert event.context == ""
        assert event.user_explicit is False


# =========================================================================
# Test TrustConfig
# =========================================================================


class TestTrustConfig:
    """Tests for TrustConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TrustConfig()

        assert config.damage_threshold == 3
        assert config.damage_window_hours == 24.0
        assert config.recovery_period_hours == 24.0
        assert config.supervised_successes_required == 5
        assert config.domain_isolation is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TrustConfig(
            damage_threshold=5,
            damage_window_hours=48.0,
            recovery_period_hours=12.0,
            supervised_successes_required=3,
        )

        assert config.damage_threshold == 5
        assert config.damage_window_hours == 48.0
        assert config.recovery_period_hours == 12.0
        assert config.supervised_successes_required == 3

    def test_severity_weights(self):
        """Test severity weights are set correctly."""
        config = TrustConfig()

        assert config.severity_weights[TrustDamageType.WRONG_ANSWER] == 1.0
        assert config.severity_weights[TrustDamageType.IGNORED_PREFERENCE] == 1.5
        assert config.severity_weights[TrustDamageType.REPETITIVE_ERROR] == 2.0
        assert config.severity_weights[TrustDamageType.SLOW_RESPONSE] == 0.3

    def test_high_impact_actions(self):
        """Test default high impact actions."""
        config = TrustConfig()

        assert "file_write" in config.high_impact_actions
        assert "file_delete" in config.high_impact_actions
        assert "git_commit" in config.high_impact_actions
        assert "external_api_call" in config.high_impact_actions
        assert "code_execution" in config.high_impact_actions


# =========================================================================
# Test TrustCircuitBreaker - Basic Operations
# =========================================================================


class TestTrustCircuitBreakerBasic:
    """Tests for basic TrustCircuitBreaker operations."""

    def test_init_default(self):
        """Test initialization with default config."""
        breaker = TrustCircuitBreaker(user_id="user123")

        assert breaker.user_id == "user123"
        assert breaker.domain == "general"
        assert breaker._state == TrustState.FULL_AUTONOMY
        assert isinstance(breaker.config, TrustConfig)

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = TrustConfig(damage_threshold=5)
        breaker = TrustCircuitBreaker(
            user_id="user123",
            config=config,
            domain="code_review",
        )

        assert breaker.config.damage_threshold == 5
        assert breaker.domain == "code_review"

    def test_state_property(self):
        """Test state property returns current state."""
        breaker = TrustCircuitBreaker(user_id="user123")

        assert breaker.state == TrustState.FULL_AUTONOMY

    def test_can_act_freely_full_autonomy(self):
        """Test can_act_freely in full autonomy state."""
        breaker = TrustCircuitBreaker(user_id="user123")

        assert breaker.can_act_freely is True

    def test_can_act_freely_reduced(self):
        """Test can_act_freely in reduced autonomy state."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.REDUCED_AUTONOMY

        assert breaker.can_act_freely is False

    def test_time_in_current_state(self):
        """Test time_in_current_state calculation."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state_changed_at = datetime.now() - timedelta(hours=2)

        time_in_state = breaker.time_in_current_state

        assert time_in_state >= timedelta(hours=1, minutes=59)
        assert time_in_state <= timedelta(hours=2, minutes=1)


# =========================================================================
# Test TrustCircuitBreaker - Damage Score
# =========================================================================


class TestDamageScore:
    """Tests for damage score calculation."""

    def test_damage_score_no_events(self):
        """Test damage score with no events."""
        breaker = TrustCircuitBreaker(user_id="user123")

        assert breaker.damage_score == 0.0

    def test_damage_score_single_event(self):
        """Test damage score with single event."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._damage_events.append(
            TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER, severity=1.0),
        )

        # Recent event should have recency factor close to 1.0
        assert breaker.damage_score >= 0.9
        assert breaker.damage_score <= 1.1

    def test_damage_score_weighted_by_type(self):
        """Test damage score is weighted by event type."""
        breaker = TrustCircuitBreaker(user_id="user123")

        # Add a repetitive error (weight 2.0)
        breaker._damage_events.append(
            TrustDamageEvent(event_type=TrustDamageType.REPETITIVE_ERROR, severity=1.0),
        )

        # Score should be close to 2.0 (weight) * 1.0 (severity) * ~1.0 (recency)
        assert breaker.damage_score >= 1.8
        assert breaker.damage_score <= 2.2

    def test_damage_score_time_decay(self):
        """Test damage score decays over time."""
        breaker = TrustCircuitBreaker(user_id="user123")

        # Add an old event (12 hours ago)
        old_event = TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER, severity=1.0)
        old_event.timestamp = datetime.now() - timedelta(hours=12)
        breaker._damage_events.append(old_event)

        # Should have reduced score due to time decay
        score = breaker.damage_score
        assert score < 1.0  # Less than full weight
        assert score > 0.4  # Still significant

    def test_damage_score_excludes_old_events(self):
        """Test damage score excludes events outside window."""
        breaker = TrustCircuitBreaker(user_id="user123")

        # Add very old event (48 hours ago, outside 24 hour window)
        old_event = TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER, severity=1.0)
        old_event.timestamp = datetime.now() - timedelta(hours=48)
        breaker._damage_events.append(old_event)

        assert breaker.damage_score == 0.0

    def test_damage_score_multiple_events(self):
        """Test damage score accumulates across events."""
        breaker = TrustCircuitBreaker(user_id="user123")

        # Add 3 wrong answer events
        for _ in range(3):
            breaker._damage_events.append(
                TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER, severity=1.0),
            )

        # Should be approximately 3.0
        assert breaker.damage_score >= 2.7
        assert breaker.damage_score <= 3.3


# =========================================================================
# Test TrustCircuitBreaker - Decision Methods
# =========================================================================


class TestDecisionMethods:
    """Tests for decision-making methods."""

    def test_should_require_confirmation_full_autonomy(self):
        """Test no confirmation needed in full autonomy."""
        breaker = TrustCircuitBreaker(user_id="user123")

        assert breaker.should_require_confirmation("file_write") is False
        assert breaker.should_require_confirmation("suggest") is False

    def test_should_require_confirmation_reduced_autonomy(self):
        """Test all actions need confirmation in reduced autonomy."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.REDUCED_AUTONOMY

        assert breaker.should_require_confirmation("file_write") is True
        assert breaker.should_require_confirmation("suggest") is True

    def test_should_require_confirmation_supervised(self):
        """Test only high-impact actions need confirmation in supervised."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED

        # High-impact actions need confirmation
        assert breaker.should_require_confirmation("file_write") is True
        assert breaker.should_require_confirmation("git_commit") is True

        # Low-impact actions don't
        assert breaker.should_require_confirmation("suggest") is False
        assert breaker.should_require_confirmation("explain") is False

    def test_get_autonomy_level_full_autonomy(self):
        """Test get_autonomy_level in full autonomy state."""
        breaker = TrustCircuitBreaker(user_id="user123")

        level = breaker.get_autonomy_level()

        assert level["state"] == "full_autonomy"
        assert level["can_act_freely"] is True
        assert level["damage_score"] == 0.0
        assert level["damage_threshold"] == 3
        assert level["recovery_progress"]["status"] == "full_trust"

    def test_get_autonomy_level_reduced_autonomy(self):
        """Test get_autonomy_level in reduced autonomy state."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.REDUCED_AUTONOMY
        breaker._state_changed_at = datetime.now()

        level = breaker.get_autonomy_level()

        assert level["state"] == "reduced_autonomy"
        assert level["can_act_freely"] is False
        assert level["recovery_progress"]["status"] == "cooling_off"

    def test_get_autonomy_level_supervised(self):
        """Test get_autonomy_level in supervised state."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 2

        level = breaker.get_autonomy_level()

        assert level["state"] == "supervised"
        assert level["recovery_progress"]["status"] == "supervised_testing"
        assert level["recovery_progress"]["successes"] == 2
        assert level["recovery_progress"]["required"] == 5


# =========================================================================
# Test TrustCircuitBreaker - Damage Recording
# =========================================================================


class TestDamageRecording:
    """Tests for damage event recording."""

    def test_record_damage_creates_event(self):
        """Test recording damage creates an event."""
        breaker = TrustCircuitBreaker(user_id="user123")

        breaker.record_damage(
            event_type=TrustDamageType.WRONG_ANSWER,
            context="Incorrect syntax suggestion",
            severity=0.7,
        )

        assert len(breaker._damage_events) == 1
        assert breaker._damage_events[0].event_type == TrustDamageType.WRONG_ANSWER
        assert breaker._damage_events[0].severity == 0.7

    def test_record_damage_string_type(self):
        """Test recording damage with string event type."""
        breaker = TrustCircuitBreaker(user_id="user123")

        breaker.record_damage(event_type="wrong_answer")

        assert len(breaker._damage_events) == 1
        assert breaker._damage_events[0].event_type == TrustDamageType.WRONG_ANSWER

    def test_record_damage_triggers_state_change(self):
        """Test recording enough damage triggers state change."""
        config = TrustConfig(damage_threshold=2)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        # Record 2 events to exceed threshold
        breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)
        state = breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)

        assert state == TrustState.REDUCED_AUTONOMY
        assert breaker._state == TrustState.REDUCED_AUTONOMY

    def test_record_damage_in_supervised_reduces_progress(self):
        """Test damage in supervised mode reduces success count."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 4

        breaker.record_damage(TrustDamageType.WRONG_ANSWER)

        # Should be reduced by 2
        assert breaker._supervised_successes == 2

    def test_record_damage_in_supervised_min_zero(self):
        """Test damage doesn't reduce successes below 0."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 1

        breaker.record_damage(TrustDamageType.WRONG_ANSWER)

        assert breaker._supervised_successes == 0


# =========================================================================
# Test TrustCircuitBreaker - Success Recording
# =========================================================================


class TestSuccessRecording:
    """Tests for success event recording."""

    def test_record_success_creates_event(self):
        """Test recording success creates an event."""
        breaker = TrustCircuitBreaker(user_id="user123")

        breaker.record_success(context="Code review accepted", user_explicit=True)

        assert len(breaker._recovery_events) == 1
        assert breaker._recovery_events[0].context == "Code review accepted"
        assert breaker._recovery_events[0].user_explicit is True

    def test_record_success_in_supervised_increments_count(self):
        """Test success in supervised mode increments count."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 2

        breaker.record_success()

        assert breaker._supervised_successes == 3

    def test_record_success_triggers_recovery(self):
        """Test enough successes triggers recovery to full autonomy."""
        config = TrustConfig(supervised_successes_required=3)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 2

        state = breaker.record_success()

        assert state == TrustState.FULL_AUTONOMY
        assert breaker._state == TrustState.FULL_AUTONOMY

    def test_record_success_in_full_autonomy_no_change(self):
        """Test success in full autonomy has no state change."""
        breaker = TrustCircuitBreaker(user_id="user123")

        state = breaker.record_success()

        assert state == TrustState.FULL_AUTONOMY


# =========================================================================
# Test TrustCircuitBreaker - State Transitions
# =========================================================================


class TestStateTransitions:
    """Tests for state transition logic."""

    def test_transition_full_to_reduced(self):
        """Test transition from full autonomy to reduced."""
        config = TrustConfig(damage_threshold=2)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        # Record enough damage
        breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)
        breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)

        assert breaker._state == TrustState.REDUCED_AUTONOMY

    def test_transition_reduced_to_supervised(self):
        """Test transition from reduced to supervised after recovery period."""
        config = TrustConfig(recovery_period_hours=0.001)  # Very short for testing
        breaker = TrustCircuitBreaker(user_id="user123", config=config)
        breaker._state = TrustState.REDUCED_AUTONOMY
        breaker._state_changed_at = datetime.now() - timedelta(hours=1)

        # Access state property to trigger check
        state = breaker.state

        assert state == TrustState.SUPERVISED

    def test_transition_supervised_to_full(self):
        """Test transition from supervised to full autonomy."""
        config = TrustConfig(supervised_successes_required=3)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)
        breaker._state = TrustState.SUPERVISED

        # Record enough successes
        breaker.record_success()
        breaker.record_success()
        breaker.record_success()

        assert breaker._state == TrustState.FULL_AUTONOMY

    def test_state_change_callback(self):
        """Test state change callback is invoked."""
        config = TrustConfig(damage_threshold=1)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        callback = MagicMock()
        breaker.on_state_change(callback)

        breaker.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)

        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] == TrustState.FULL_AUTONOMY
        assert args[1] == TrustState.REDUCED_AUTONOMY

    def test_recovery_clears_old_events(self):
        """Test transition to full autonomy clears old damage events."""
        config = TrustConfig(supervised_successes_required=1)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        # Add old damage event
        old_event = TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER)
        old_event.timestamp = datetime.now() - timedelta(hours=72)
        breaker._damage_events.append(old_event)

        breaker._state = TrustState.SUPERVISED
        breaker.record_success()

        # Old events should be cleared
        assert len(breaker._damage_events) == 0


# =========================================================================
# Test TrustCircuitBreaker - Manual Controls
# =========================================================================


class TestManualControls:
    """Tests for manual control methods."""

    def test_reset_returns_to_full_autonomy(self):
        """Test reset returns to full autonomy."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.REDUCED_AUTONOMY
        breaker._damage_events.append(TrustDamageEvent(event_type=TrustDamageType.WRONG_ANSWER))

        breaker.reset()

        assert breaker._state == TrustState.FULL_AUTONOMY
        assert len(breaker._damage_events) == 0

    def test_reset_clears_supervised_successes(self):
        """Test reset clears supervised success count."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.SUPERVISED
        breaker._supervised_successes = 3

        breaker.reset()

        assert breaker._supervised_successes == 0

    def test_reset_triggers_callback(self):
        """Test reset triggers state change callback."""
        breaker = TrustCircuitBreaker(user_id="user123")
        breaker._state = TrustState.REDUCED_AUTONOMY

        callback = MagicMock()
        breaker.on_state_change(callback)

        breaker.reset()

        callback.assert_called_once_with(TrustState.REDUCED_AUTONOMY, TrustState.FULL_AUTONOMY)


# =========================================================================
# Test TrustCircuitBreaker - Serialization
# =========================================================================


class TestSerialization:
    """Tests for serialization/deserialization."""

    def test_to_dict(self):
        """Test serializing to dictionary."""
        config = TrustConfig(damage_threshold=5, recovery_period_hours=48.0)
        breaker = TrustCircuitBreaker(
            user_id="user123",
            config=config,
            domain="code_review",
        )
        breaker._damage_events.append(
            TrustDamageEvent(
                event_type=TrustDamageType.WRONG_ANSWER,
                context="Bad suggestion",
                severity=0.8,
            ),
        )

        data = breaker.to_dict()

        assert data["user_id"] == "user123"
        assert data["domain"] == "code_review"
        assert data["state"] == "full_autonomy"
        assert data["config"]["damage_threshold"] == 5
        assert len(data["damage_events"]) == 1
        assert data["damage_events"][0]["event_type"] == "wrong_answer"

    def test_from_dict(self):
        """Test deserializing from dictionary."""
        data = {
            "user_id": "user123",
            "domain": "testing",
            "state": "supervised",
            "state_changed_at": datetime.now().isoformat(),
            "supervised_successes": 3,
            "damage_events": [
                {
                    "event_type": "wrong_answer",
                    "timestamp": datetime.now().isoformat(),
                    "context": "Test error",
                    "severity": 0.5,
                    "user_explicit": False,
                },
            ],
            "config": {
                "damage_threshold": 4,
                "recovery_period_hours": 12.0,
                "supervised_successes_required": 8,
            },
        }

        breaker = TrustCircuitBreaker.from_dict(data)

        assert breaker.user_id == "user123"
        assert breaker.domain == "testing"
        assert breaker._state == TrustState.SUPERVISED
        assert breaker._supervised_successes == 3
        assert breaker.config.damage_threshold == 4
        assert len(breaker._damage_events) == 1

    def test_round_trip_serialization(self):
        """Test serialization round-trip preserves state."""
        breaker = TrustCircuitBreaker(user_id="user123", domain="testing")
        breaker.record_damage(TrustDamageType.WRONG_ANSWER, context="Error 1")
        breaker.record_damage(TrustDamageType.IGNORED_PREFERENCE, context="Error 2")

        data = breaker.to_dict()
        restored = TrustCircuitBreaker.from_dict(data)

        assert restored.user_id == breaker.user_id
        assert restored.domain == breaker.domain
        assert restored._state == breaker._state
        assert len(restored._damage_events) == len(breaker._damage_events)


# =========================================================================
# Test create_trust_breaker Factory
# =========================================================================


class TestCreateTrustBreaker:
    """Tests for create_trust_breaker factory function."""

    def test_create_default(self):
        """Test creating breaker with defaults."""
        breaker = create_trust_breaker(user_id="user123")

        assert breaker.user_id == "user123"
        assert breaker.domain == "general"
        assert breaker.config.damage_threshold == 3  # Default

    def test_create_with_domain(self):
        """Test creating breaker with custom domain."""
        breaker = create_trust_breaker(user_id="user123", domain="code_review")

        assert breaker.domain == "code_review"

    def test_create_strict_mode(self):
        """Test creating breaker in strict mode."""
        breaker = create_trust_breaker(user_id="user123", strict=True)

        assert breaker.config.damage_threshold == 2  # Stricter
        assert breaker.config.recovery_period_hours == 48.0  # Longer
        assert breaker.config.supervised_successes_required == 10  # More required


# =========================================================================
# Integration Tests
# =========================================================================


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_damage_recovery_cycle(self):
        """Test complete cycle: full autonomy -> damage -> recovery."""
        config = TrustConfig(
            damage_threshold=2,
            recovery_period_hours=0.001,  # Very short for testing
            supervised_successes_required=2,
        )
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        # Start in full autonomy
        assert breaker.state == TrustState.FULL_AUTONOMY
        assert breaker.can_act_freely is True

        # Record damage
        breaker.record_damage(TrustDamageType.WRONG_ANSWER)
        assert breaker.state == TrustState.FULL_AUTONOMY  # Not enough yet

        breaker.record_damage(TrustDamageType.WRONG_ANSWER)
        assert breaker.state == TrustState.REDUCED_AUTONOMY
        assert breaker.can_act_freely is False

        # Wait for recovery period (simulated)
        breaker._state_changed_at = datetime.now() - timedelta(hours=1)

        # Access state to trigger check
        assert breaker.state == TrustState.SUPERVISED

        # Record successes
        breaker.record_success()
        assert breaker.state == TrustState.SUPERVISED  # Not enough yet

        breaker.record_success()
        assert breaker.state == TrustState.FULL_AUTONOMY
        assert breaker.can_act_freely is True

    def test_damage_in_supervised_extends_recovery(self):
        """Test that damage in supervised mode delays recovery."""
        config = TrustConfig(supervised_successes_required=3)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)
        breaker._state = TrustState.SUPERVISED

        # Record 2 successes
        breaker.record_success()
        breaker.record_success()
        assert breaker._supervised_successes == 2

        # Record damage (reduces by 2)
        breaker.record_damage(TrustDamageType.WRONG_ANSWER)
        assert breaker._supervised_successes == 0

        # Need to start over
        breaker.record_success()
        breaker.record_success()
        breaker.record_success()
        assert breaker.state == TrustState.FULL_AUTONOMY

    def test_multiple_domains(self):
        """Test trust is isolated per domain."""
        code_review = TrustCircuitBreaker(user_id="user123", domain="code_review")
        documentation = TrustCircuitBreaker(user_id="user123", domain="documentation")

        # Damage in code review
        code_review.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)
        code_review.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)
        code_review.record_damage(TrustDamageType.WRONG_ANSWER, severity=1.0)

        # Code review should be damaged, but documentation unaffected
        assert code_review.state == TrustState.REDUCED_AUTONOMY
        assert documentation.state == TrustState.FULL_AUTONOMY

    def test_weighted_damage_types(self):
        """Test that different damage types have different impacts."""
        config = TrustConfig(damage_threshold=3)
        breaker = TrustCircuitBreaker(user_id="user123", config=config)

        # Slow response (weight 0.3) - shouldn't trigger threshold
        breaker.record_damage(TrustDamageType.SLOW_RESPONSE)
        assert breaker.state == TrustState.FULL_AUTONOMY

        # Repetitive error (weight 2.0) - should push over threshold
        breaker.record_damage(TrustDamageType.REPETITIVE_ERROR)
        # Score is now approximately 0.3 + 2.0 = 2.3, still under 3
        assert breaker.state == TrustState.FULL_AUTONOMY

        # Another wrong answer (weight 1.0) - should push over
        breaker.record_damage(TrustDamageType.WRONG_ANSWER)
        # Score is now approximately 0.3 + 2.0 + 1.0 = 3.3, over threshold
        assert breaker.state == TrustState.REDUCED_AUTONOMY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
