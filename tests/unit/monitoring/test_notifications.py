"""Tests for notification delivery channels.

Covers: deliver_notification, deliver_email, deliver_stdout.
(deliver_webhook already tested in test_alerts.py)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from attune.monitoring.models import (
    AlertChannel,
    AlertConfig,
    AlertEvent,
    AlertMetric,
    AlertSeverity,
)
from attune.monitoring.notifications import (
    deliver_email,
    deliver_notification,
    deliver_stdout,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_alert(
    channel: AlertChannel = AlertChannel.STDOUT,
    webhook_url: str | None = None,
    email: str | None = None,
) -> AlertConfig:
    return AlertConfig(
        alert_id="alert-1",
        name="Test Alert",
        metric=AlertMetric.ERROR_RATE,
        threshold=0.5,
        channel=channel,
        webhook_url=webhook_url,
        email=email,
    )


def _make_event() -> AlertEvent:
    return AlertEvent(
        alert_id="alert-1",
        alert_name="Test Alert",
        metric=AlertMetric.ERROR_RATE,
        current_value=0.75,
        threshold=0.5,
        severity=AlertSeverity.WARNING,
        triggered_at=datetime(2026, 3, 20, 12, 0, 0),
        message="Error rate exceeded threshold",
    )


# ------------------------------------------------------------------
# deliver_notification
# ------------------------------------------------------------------


class TestDeliverNotification:
    """Tests for deliver_notification routing."""

    def test_routes_to_webhook(self):
        """WEBHOOK channel routes to deliver_webhook."""
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url="https://example.com/hook")
        event = _make_event()

        with patch("attune.monitoring.notifications.deliver_webhook", return_value=True) as mock:
            result = deliver_notification(alert, event)

        assert result is True
        mock.assert_called_once_with(alert, event)

    def test_routes_to_email(self):
        """EMAIL channel routes to deliver_email."""
        alert = _make_alert(AlertChannel.EMAIL, email="test@example.com")
        event = _make_event()

        with patch("attune.monitoring.notifications.deliver_email", return_value=True) as mock:
            result = deliver_notification(alert, event)

        assert result is True
        mock.assert_called_once_with(alert, event)

    def test_routes_to_stdout(self):
        """STDOUT channel routes to deliver_stdout."""
        alert = _make_alert(AlertChannel.STDOUT)
        event = _make_event()

        with patch("attune.monitoring.notifications.deliver_stdout", return_value=True) as mock:
            result = deliver_notification(alert, event)

        assert result is True
        mock.assert_called_once_with(event)

    def test_routes_vscode_output_to_stdout(self):
        """VSCODE_OUTPUT channel also routes to deliver_stdout."""
        alert = _make_alert(AlertChannel.VSCODE_OUTPUT)
        event = _make_event()

        with patch("attune.monitoring.notifications.deliver_stdout", return_value=True) as mock:
            result = deliver_notification(alert, event)

        assert result is True
        mock.assert_called_once_with(event)

    def test_exception_returns_false(self):
        """Exception during delivery returns False."""
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url="https://example.com/hook")
        event = _make_event()

        with patch(
            "attune.monitoring.notifications.deliver_webhook",
            side_effect=RuntimeError("boom"),
        ):
            result = deliver_notification(alert, event)

        assert result is False


# ------------------------------------------------------------------
# deliver_email
# ------------------------------------------------------------------


class TestDeliverEmail:
    """Tests for deliver_email."""

    def test_no_email_returns_false(self):
        """Returns False when alert has no email configured."""
        alert = _make_alert(AlertChannel.EMAIL, email=None)
        event = _make_event()

        result = deliver_email(alert, event)

        assert result is False

    def test_sends_email_via_smtp(self):
        """Sends email through SMTP with correct subject."""
        alert = _make_alert(AlertChannel.EMAIL, email="test@example.com")
        event = _make_event()

        mock_smtp = MagicMock()
        with (
            patch.dict(
                "os.environ",
                {
                    "SMTP_HOST": "mail.test.com",
                    "SMTP_PORT": "587",
                    "SMTP_USER": "user",
                    "SMTP_PASSWORD": "pass",
                    "SMTP_FROM": "alerts@test.com",
                },
            ),
            patch("attune.monitoring.notifications.smtplib.SMTP", return_value=mock_smtp),
        ):
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            result = deliver_email(alert, event)

        assert result is True
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("user", "pass")
        mock_smtp.sendmail.assert_called_once()

    def test_sends_without_auth_when_no_credentials(self):
        """Sends without TLS/login when no SMTP_USER set."""
        alert = _make_alert(AlertChannel.EMAIL, email="test@example.com")
        event = _make_event()

        mock_smtp = MagicMock()
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("attune.monitoring.notifications.smtplib.SMTP", return_value=mock_smtp),
        ):
            mock_smtp.__enter__ = MagicMock(return_value=mock_smtp)
            mock_smtp.__exit__ = MagicMock(return_value=False)
            result = deliver_email(alert, event)

        assert result is True
        mock_smtp.starttls.assert_not_called()
        mock_smtp.login.assert_not_called()

    def test_smtp_error_returns_false(self):
        """SMTP exception returns False."""
        import smtplib

        alert = _make_alert(AlertChannel.EMAIL, email="test@example.com")
        event = _make_event()

        with patch(
            "attune.monitoring.notifications.smtplib.SMTP",
            side_effect=smtplib.SMTPException("connection failed"),
        ):
            result = deliver_email(alert, event)

        assert result is False


# ------------------------------------------------------------------
# deliver_stdout
# ------------------------------------------------------------------


class TestDeliverStdout:
    """Tests for deliver_stdout."""

    def test_prints_message(self, capsys):
        """Prints event message to stdout."""
        event = _make_event()

        result = deliver_stdout(event)

        assert result is True
        captured = capsys.readouterr()
        assert event.message in captured.out
        assert "=" * 60 in captured.out

    def test_returns_true(self):
        """Always returns True."""
        event = _make_event()

        result = deliver_stdout(event)

        assert result is True
