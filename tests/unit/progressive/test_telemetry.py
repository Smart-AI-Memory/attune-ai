"""Unit tests for progressive workflow telemetry.

Tests cover:
- Tier execution tracking
- Escalation tracking
- Budget exceeded tracking
- Custom event tracking
- Provider inference
- User ID hashing
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from attune.workflows.progressive.core import (
    FailureAnalysis,
    Tier,
    TierResult,
)
from attune.workflows.progressive.telemetry import ProgressiveTelemetry


class TestProgressiveTelemetry:
    """Test ProgressiveTelemetry class."""

    def test_init(self):
        """Test telemetry initialization."""
        telemetry = ProgressiveTelemetry("test-workflow", user_id="test-user")

        assert telemetry.workflow_name == "test-workflow"
        assert telemetry.user_id == "test-user"
        assert telemetry.tracker is not None

    def test_init_without_user_id(self):
        """Test telemetry initialization without user ID."""
        telemetry = ProgressiveTelemetry("test-workflow")

        assert telemetry.workflow_name == "test-workflow"
        assert telemetry.user_id is None

    @patch("attune.workflows.progressive.telemetry.UsageTracker")
    def test_track_tier_execution_success(self, mock_tracker_class):
        """Test successful tier execution tracking."""
        mock_tracker = MagicMock()
        mock_tracker_class.get_instance.return_value = mock_tracker

        telemetry = ProgressiveTelemetry("test-workflow", user_id="test-user")

        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            cost=0.30,
            duration=15.5,
            tokens_used={"input": 1000, "output": 500, "total": 1500},
            failure_analysis=FailureAnalysis(),
        )

        telemetry.track_tier_execution(
            tier_result,
            attempt=1,
            escalated=False,
            escalation_reason=None,
        )

        # Verify tracker was called
        mock_tracker.track_llm_call.assert_called_once()
        call_args = mock_tracker.track_llm_call.call_args[1]
        assert call_args["workflow"] == "test-workflow"
        assert call_args["stage"] == "tier-cheap-attempt-1"
        assert call_args["tier"] == "CHEAP"
        assert call_args["model"] == "gpt-4o-mini"
        assert call_args["provider"] == "openai"
        assert call_args["cost"] == 0.30
        assert call_args["duration_ms"] == 15500

    @patch("attune.workflows.progressive.telemetry.UsageTracker")
    def test_track_tier_execution_handles_exception(self, mock_tracker_class, caplog):
        """Test tier execution tracking handles tracker exceptions."""
        mock_tracker = MagicMock()
        mock_tracker.track_llm_call.side_effect = Exception("Tracker error")
        mock_tracker_class.get_instance.return_value = mock_tracker

        telemetry = ProgressiveTelemetry("test-workflow")

        tier_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            cost=0.30,
            duration=15.5,
            tokens_used={},
            failure_analysis=FailureAnalysis(),
        )

        # Should not raise, just log warning
        telemetry.track_tier_execution(tier_result, attempt=1, escalated=False)

        assert "Failed to track tier execution" in caplog.text

    def test_track_escalation(self, tmp_path, monkeypatch):
        """Test escalation tracking."""
        # Use tmp_path for telemetry directory
        telemetry_dir = tmp_path / ".attune" / "telemetry"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow", user_id="test-user")

        telemetry.track_escalation(
            from_tier=Tier.CHEAP,
            to_tier=Tier.CAPABLE,
            reason="Low quality score",
            item_count=10,
            current_cost=0.50,
        )

        # Verify event was written
        events_file = telemetry_dir / "progressive_events.jsonl"
        assert events_file.exists()

        # Read and verify event
        with events_file.open() as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "progressive_escalation"
        assert event["workflow"] == "test-workflow"
        assert event["from_tier"] == "cheap"
        assert event["to_tier"] == "capable"
        assert event["reason"] == "Low quality score"
        assert event["item_count"] == 10
        assert event["current_cost"] == 0.50
        assert "user_id_hash" in event

    def test_track_budget_exceeded(self, tmp_path, monkeypatch, caplog):
        """Test budget exceeded tracking."""
        telemetry_dir = tmp_path / ".attune" / "telemetry"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow")

        telemetry.track_budget_exceeded(current_cost=7.50, max_budget=5.00, action="abort")

        # Verify event was written
        events_file = telemetry_dir / "progressive_events.jsonl"
        assert events_file.exists()

        with events_file.open() as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "progressive_budget_exceeded"
        assert event["workflow"] == "test-workflow"
        assert event["current_cost"] == 7.50
        assert event["max_budget"] == 5.00
        assert event["overage"] == 2.50
        assert event["action"] == "abort"

        # Verify warning was logged
        assert "Budget exceeded" in caplog.text

    def test_track_custom_event_success(self, tmp_path, monkeypatch):
        """Test custom event tracking."""
        telemetry_dir = tmp_path / ".attune" / "telemetry"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow", user_id="user123")

        telemetry._track_custom_event(event_type="test_event", data={"key": "value", "count": 42})

        # Verify event was written
        events_file = telemetry_dir / "progressive_events.jsonl"
        assert events_file.exists()

        with events_file.open() as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "test_event"
        assert event["key"] == "value"
        assert event["count"] == 42
        assert "timestamp" in event
        assert "user_id_hash" in event

    def test_track_custom_event_handles_write_error(self, tmp_path, monkeypatch, caplog):
        """Test custom event tracking handles write errors."""
        # Make telemetry dir read-only to cause write error
        telemetry_dir = tmp_path / ".attune" / "telemetry"
        telemetry_dir.mkdir(parents=True)
        telemetry_dir.chmod(0o444)  # Read-only

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow")

        # Should not raise, just log debug message
        telemetry._track_custom_event(event_type="test_event", data={})

        # Note: debug messages may not appear in caplog depending on config
        # Just verify no exception was raised

    def test_track_custom_event_anonymous_user(self, tmp_path, monkeypatch):
        """Test custom event tracking with no user ID."""
        telemetry_dir = tmp_path / ".attune" / "telemetry"
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow", user_id=None)

        telemetry._track_custom_event(event_type="test_event", data={})

        events_file = telemetry_dir / "progressive_events.jsonl"
        with events_file.open() as f:
            event = json.loads(f.readline())

        assert event["user_id_hash"] == "anonymous"


class TestGetProvider:
    """Test provider inference from model names."""

    def test_get_provider_openai(self):
        """Test OpenAI model detection."""
        assert ProgressiveTelemetry._get_provider("gpt-4o") == "openai"
        assert ProgressiveTelemetry._get_provider("gpt-4o-mini") == "openai"
        assert ProgressiveTelemetry._get_provider("GPT-4") == "openai"

    def test_get_provider_anthropic(self):
        """Test Anthropic model detection."""
        assert ProgressiveTelemetry._get_provider("claude-3-5-sonnet") == "anthropic"
        assert ProgressiveTelemetry._get_provider("claude-opus-4") == "anthropic"
        assert ProgressiveTelemetry._get_provider("Claude-Haiku") == "anthropic"

    def test_get_provider_google(self):
        """Test Google model detection."""
        assert ProgressiveTelemetry._get_provider("gemini-pro") == "google"
        assert ProgressiveTelemetry._get_provider("gemini-1.5-flash") == "google"
        assert ProgressiveTelemetry._get_provider("Gemini-Ultra") == "google"

    def test_get_provider_unknown(self):
        """Test unknown model provider."""
        assert ProgressiveTelemetry._get_provider("custom-model") == "unknown"
        assert ProgressiveTelemetry._get_provider("llama-2") == "unknown"
        assert ProgressiveTelemetry._get_provider("") == "unknown"


class TestHashUserId:
    """Test user ID hashing for privacy."""

    def test_hash_user_id_deterministic(self):
        """Test that hashing is deterministic."""
        hash1 = ProgressiveTelemetry._hash_user_id("test-user")
        hash2 = ProgressiveTelemetry._hash_user_id("test-user")

        assert hash1 == hash2

    def test_hash_user_id_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = ProgressiveTelemetry._hash_user_id("user1")
        hash2 = ProgressiveTelemetry._hash_user_id("user2")

        assert hash1 != hash2

    def test_hash_user_id_format(self):
        """Test that hash is a valid SHA256 hex string."""
        hash_result = ProgressiveTelemetry._hash_user_id("test-user")

        assert len(hash_result) == 64  # SHA256 produces 64 hex chars
        assert all(c in "0123456789abcdef" for c in hash_result)

    def test_hash_user_id_empty_string(self):
        """Test hashing empty string."""
        hash_result = ProgressiveTelemetry._hash_user_id("")

        assert len(hash_result) == 64  # Still valid hash


class TestTelemetryIntegration:
    """Integration tests for telemetry tracking."""

    @patch("attune.workflows.progressive.telemetry.UsageTracker")
    def test_multiple_tier_executions(self, mock_tracker_class, tmp_path, monkeypatch):
        """Test tracking multiple tier executions."""
        mock_tracker = MagicMock()
        mock_tracker_class.get_instance.return_value = mock_tracker

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        telemetry = ProgressiveTelemetry("test-workflow", user_id="user123")

        # Track cheap tier
        cheap_result = TierResult(
            tier=Tier.CHEAP,
            model="gpt-4o-mini",
            attempt=1,
            timestamp=datetime.now(),
            cost=0.30,
            duration=10.0,
            tokens_used={"total": 1000},
            failure_analysis=FailureAnalysis(),
        )
        telemetry.track_tier_execution(cheap_result, attempt=1, escalated=True)

        # Track escalation
        telemetry.track_escalation(
            from_tier=Tier.CHEAP,
            to_tier=Tier.CAPABLE,
            reason="Low CQS",
            item_count=5,
            current_cost=0.30,
        )

        # Track capable tier
        capable_result = TierResult(
            tier=Tier.CAPABLE,
            model="claude-3-5-sonnet",
            attempt=1,
            timestamp=datetime.now(),
            cost=0.75,
            duration=20.0,
            tokens_used={"total": 2000},
            failure_analysis=FailureAnalysis(),
        )
        telemetry.track_tier_execution(capable_result, attempt=1, escalated=False)

        # Verify all tracker calls
        assert mock_tracker.track_llm_call.call_count == 2

        # Verify events file has escalation event
        events_file = tmp_path / ".attune" / "telemetry" / "progressive_events.jsonl"
        assert events_file.exists()

        with events_file.open() as f:
            event = json.loads(f.readline())

        assert event["event_type"] == "progressive_escalation"
