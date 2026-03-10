"""Tests for alert system.

Tests the AlertEngine, notification delivery, and CLI commands.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import socket
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.monitoring.alerts import (
    AlertChannel,
    AlertConfig,
    AlertEngine,
    AlertEvent,
    AlertMetric,
    AlertSeverity,
    get_alert_engine,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "alerts.db"
        yield db_path


@pytest.fixture
def temp_telemetry():
    """Create a temporary telemetry directory with test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        telemetry_dir = Path(tmpdir)
        usage_file = telemetry_dir / "usage.jsonl"

        # Create test telemetry data
        entries = [
            {
                "timestamp": datetime.now().isoformat(),
                "workflow": "test-workflow",
                "cost": 5.0,
                "tokens": {"total": 1000},
                "duration_ms": 500,
            },
            {
                "timestamp": datetime.now().isoformat(),
                "workflow": "test-workflow",
                "cost": 3.0,
                "tokens": {"total": 800},
                "duration_ms": 400,
                "error": True,  # This is an error
            },
        ]

        with open(usage_file, "w") as f:
            f.writelines(json.dumps(entry) + "\n" for entry in entries)

        yield telemetry_dir


class TestAlertConfig:
    """Tests for AlertConfig dataclass."""

    def test_to_dict(self):
        """Test AlertConfig serialization."""
        config = AlertConfig(
            alert_id="test_alert",
            name="Test Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.WEBHOOK,
            webhook_url="https://example.com/webhook",
        )

        data = config.to_dict()

        assert data["alert_id"] == "test_alert"
        assert data["metric"] == "daily_cost"
        assert data["channel"] == "webhook"
        assert data["threshold"] == 10.0

    def test_from_dict(self):
        """Test AlertConfig deserialization."""
        data = {
            "alert_id": "test_alert",
            "name": "Test Alert",
            "metric": "daily_cost",
            "threshold": 10.0,
            "channel": "webhook",
            "webhook_url": "https://example.com/webhook",
        }

        config = AlertConfig.from_dict(data)

        assert config.alert_id == "test_alert"
        assert config.metric == AlertMetric.DAILY_COST
        assert config.channel == AlertChannel.WEBHOOK


class TestAlertEngine:
    """Tests for AlertEngine class."""

    def test_init_creates_database(self, temp_db):
        """Test that initialization creates the database."""
        AlertEngine(db_path=temp_db)

        assert temp_db.exists()

        # Verify tables exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "alerts" in tables
        assert "alert_history" in tables

    def test_add_alert(self, temp_db):
        """Test adding an alert."""
        engine = AlertEngine(db_path=temp_db)

        config = engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.STDOUT,
        )

        assert config.alert_id == "cost_alert"
        assert config.metric == AlertMetric.DAILY_COST
        assert config.threshold == 10.0

    def test_add_alert_with_string_enums(self, temp_db):
        """Test adding an alert with string metric/channel values."""
        engine = AlertEngine(db_path=temp_db)

        config = engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric="daily_cost",  # String instead of enum
            threshold=10.0,
            channel="stdout",  # String instead of enum
        )

        assert config.metric == AlertMetric.DAILY_COST
        assert config.channel == AlertChannel.STDOUT

    def test_add_alert_webhook_requires_url(self, temp_db):
        """Test that webhook channel requires URL."""
        engine = AlertEngine(db_path=temp_db)

        with pytest.raises(ValueError, match="webhook_url required"):
            engine.add_alert(
                alert_id="test",
                name="Test",
                metric=AlertMetric.DAILY_COST,
                threshold=10.0,
                channel=AlertChannel.WEBHOOK,
            )

    def test_add_alert_email_requires_address(self, temp_db):
        """Test that email channel requires email address."""
        engine = AlertEngine(db_path=temp_db)

        with pytest.raises(ValueError, match="email required"):
            engine.add_alert(
                alert_id="test",
                name="Test",
                metric=AlertMetric.DAILY_COST,
                threshold=10.0,
                channel=AlertChannel.EMAIL,
            )

    def test_list_alerts(self, temp_db):
        """Test listing alerts."""
        engine = AlertEngine(db_path=temp_db)

        engine.add_alert(
            alert_id="alert1",
            name="Alert 1",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.STDOUT,
        )
        engine.add_alert(
            alert_id="alert2",
            name="Alert 2",
            metric=AlertMetric.ERROR_RATE,
            threshold=5.0,
            channel=AlertChannel.STDOUT,
        )

        alerts = engine.list_alerts()

        assert len(alerts) == 2
        alert_ids = {a.alert_id for a in alerts}
        assert "alert1" in alert_ids
        assert "alert2" in alert_ids

    def test_get_alert(self, temp_db):
        """Test getting a specific alert."""
        engine = AlertEngine(db_path=temp_db)

        engine.add_alert(
            alert_id="my_alert",
            name="My Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=15.0,
            channel=AlertChannel.STDOUT,
        )

        alert = engine.get_alert("my_alert")

        assert alert is not None
        assert alert.alert_id == "my_alert"
        assert alert.threshold == 15.0

    def test_get_alert_not_found(self, temp_db):
        """Test getting a non-existent alert."""
        engine = AlertEngine(db_path=temp_db)

        alert = engine.get_alert("nonexistent")

        assert alert is None

    def test_delete_alert(self, temp_db):
        """Test deleting an alert."""
        engine = AlertEngine(db_path=temp_db)

        engine.add_alert(
            alert_id="to_delete",
            name="To Delete",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.STDOUT,
        )

        deleted = engine.delete_alert("to_delete")

        assert deleted is True
        assert engine.get_alert("to_delete") is None

    def test_delete_alert_not_found(self, temp_db):
        """Test deleting a non-existent alert."""
        engine = AlertEngine(db_path=temp_db)

        deleted = engine.delete_alert("nonexistent")

        assert deleted is False

    def test_enable_disable_alert(self, temp_db):
        """Test enabling and disabling alerts."""
        engine = AlertEngine(db_path=temp_db)

        engine.add_alert(
            alert_id="toggle_alert",
            name="Toggle Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.STDOUT,
        )

        # Disable
        engine.disable_alert("toggle_alert")
        alert = engine.get_alert("toggle_alert")
        assert alert.enabled is False

        # Enable
        engine.enable_alert("toggle_alert")
        alert = engine.get_alert("toggle_alert")
        assert alert.enabled is True


class TestAlertEngineMetrics:
    """Tests for metrics retrieval."""

    def test_get_metrics_with_data(self, temp_db, temp_telemetry):
        """Test getting metrics from telemetry data."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        metrics = engine.get_metrics()

        assert metrics["daily_cost"] == 8.0  # 5 + 3
        assert metrics["token_usage"] == 1800  # 1000 + 800
        assert metrics["error_rate"] == 50.0  # 1 error out of 2 calls
        assert metrics["avg_latency"] == 450.0  # (500 + 400) / 2

    def test_get_metrics_no_telemetry(self, temp_db):
        """Test getting metrics when no telemetry data exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = AlertEngine(db_path=temp_db, telemetry_dir=tmpdir)

            metrics = engine.get_metrics()

            assert metrics["daily_cost"] == 0.0
            assert metrics["error_rate"] == 0.0
            assert metrics["avg_latency"] == 0.0
            assert metrics["token_usage"] == 0


class TestAlertEngineTriggering:
    """Tests for alert triggering and notification."""

    def test_check_and_trigger_no_alerts(self, temp_db, temp_telemetry):
        """Test check_and_trigger with no configured alerts."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        events = engine.check_and_trigger()

        assert events == []

    def test_check_and_trigger_threshold_exceeded(self, temp_db, temp_telemetry):
        """Test alert triggers when threshold is exceeded."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        # Add alert with threshold below current metrics
        engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=5.0,  # Current is 8.0
            channel=AlertChannel.STDOUT,
        )

        events = engine.check_and_trigger()

        assert len(events) == 1
        assert events[0].alert_id == "cost_alert"
        assert events[0].current_value == 8.0
        assert events[0].threshold == 5.0

    def test_check_and_trigger_threshold_not_exceeded(self, temp_db, temp_telemetry):
        """Test no alert triggers when threshold is not exceeded."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        # Add alert with threshold above current metrics
        engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=100.0,  # Current is 8.0
            channel=AlertChannel.STDOUT,
        )

        events = engine.check_and_trigger()

        assert events == []

    def test_check_and_trigger_disabled_alert(self, temp_db, temp_telemetry):
        """Test disabled alerts don't trigger."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=5.0,  # Would trigger
            channel=AlertChannel.STDOUT,
        )
        engine.disable_alert("cost_alert")

        events = engine.check_and_trigger()

        assert events == []

    def test_check_and_trigger_cooldown(self, temp_db, temp_telemetry):
        """Test cooldown prevents repeated alerts."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=5.0,
            channel=AlertChannel.STDOUT,
            cooldown_seconds=3600,  # 1 hour cooldown
        )

        # First check triggers
        events1 = engine.check_and_trigger()
        assert len(events1) == 1

        # Immediate second check doesn't trigger (cooldown)
        events2 = engine.check_and_trigger()
        assert events2 == []

    def test_alert_history_recorded(self, temp_db, temp_telemetry):
        """Test that triggered alerts are recorded in history."""
        engine = AlertEngine(db_path=temp_db, telemetry_dir=temp_telemetry)

        engine.add_alert(
            alert_id="cost_alert",
            name="Daily Cost Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=5.0,
            channel=AlertChannel.STDOUT,
        )

        engine.check_and_trigger()

        history = engine.get_alert_history()

        assert len(history) == 1
        assert history[0]["alert_id"] == "cost_alert"
        assert history[0]["current_value"] == 8.0


class TestWebhookDelivery:
    """Tests for webhook notification delivery."""

    @patch("attune.monitoring.notifications.build_opener")
    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_deliver_webhook_success(self, mock_dns, mock_build_opener, temp_db):
        """Test successful webhook delivery."""
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_build_opener.return_value = mock_opener

        engine = AlertEngine(db_path=temp_db)

        alert = AlertConfig(
            alert_id="test",
            name="Test",
            metric=AlertMetric.DAILY_COST,
            threshold=10.0,
            channel=AlertChannel.WEBHOOK,
            webhook_url="https://example.com/webhook",
        )

        event = AlertEvent(
            alert_id="test",
            alert_name="Test",
            metric=AlertMetric.DAILY_COST,
            current_value=15.0,
            threshold=10.0,
            severity=AlertSeverity.WARNING,
            triggered_at=datetime.now(),
            message="Test message",
        )

        result = engine._deliver_webhook(alert, event)

        assert result is True
        mock_opener.open.assert_called_once()


class TestGetAlertEngine:
    """Tests for the get_alert_engine factory function."""

    def test_get_alert_engine_default_path(self):
        """Test get_alert_engine with default path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / ".empathy" / "alerts.db"

            engine = get_alert_engine(db_path=db_path)

            assert isinstance(engine, AlertEngine)
            assert engine.db_path == db_path
