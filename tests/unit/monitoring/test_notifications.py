"""Tests for notification delivery channels.

Covers: deliver_notification, deliver_email, deliver_stdout, and the
deliver_webhook edge cases (missing URL, invalid URL, non-200 status,
redirect blocking, URLError) not already exercised by
TestWebhookDelivery in test_alerts.py (which covers the happy path).
"""

from __future__ import annotations

import ssl
import urllib.error
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

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
    deliver_webhook,
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

    def test_unknown_channel_returns_false(self):
        """An unrecognized channel value falls through to the default branch.

        Every real AlertChannel member is handled explicitly, so this
        exercises the defensive else-branch by substituting a fake
        channel object after construction (AlertConfig is a plain,
        unvalidated dataclass, so this is a legal runtime shape — e.g.
        a value read back from a stale/foreign serialized config).
        """
        alert = _make_alert(AlertChannel.STDOUT)
        alert.channel = SimpleNamespace(value="carrier_pigeon")
        event = _make_event()

        result = deliver_notification(alert, event)

        assert result is False


# ------------------------------------------------------------------
# deliver_webhook
# ------------------------------------------------------------------


class TestDeliverWebhook:
    """Edge cases for deliver_webhook beyond the happy path.

    The success path (200 response) is covered by
    TestWebhookDelivery.test_deliver_webhook_success in test_alerts.py.
    """

    def test_no_webhook_url_returns_false(self):
        """Returns False immediately when alert has no webhook_url."""
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url=None)
        event = _make_event()

        result = deliver_webhook(alert, event)

        assert result is False

    def test_invalid_webhook_url_returns_false(self):
        """A URL blocked by SSRF validation (e.g. localhost) returns False."""
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url="http://localhost/hook")
        event = _make_event()

        result = deliver_webhook(alert, event)

        assert result is False

    @patch("attune.monitoring.notifications.build_opener")
    def test_non_200_status_returns_false(self, mock_build_opener):
        """A non-200 response status is treated as delivery failure."""
        # Public IP literal avoids needing a DNS mock for validation.
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url="http://8.8.8.8/hook")
        event = _make_event()

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response

        captured: dict[str, type] = {}

        def _capture_handler(*handler_classes):
            # First handler is the redirect blocker; the pinned
            # http/https handlers follow (DNS-rebinding guard).
            captured["handler_cls"] = handler_classes[0]
            return mock_opener

        mock_build_opener.side_effect = _capture_handler

        result = deliver_webhook(alert, event)

        assert result is False
        mock_opener.open.assert_called_once()

        # The redirect-blocking handler only runs its body when urllib
        # actually encounters a 3xx response, which doesn't happen with
        # a mocked opener. Exercise it directly to cover the SSRF guard.
        handler = captured["handler_cls"]()
        with pytest.raises(urllib.error.HTTPError):
            handler.redirect_request(None, None, 302, "Found", {}, "http://evil.example/")

    @patch("attune.monitoring.notifications.build_opener")
    def test_url_error_returns_false(self, mock_build_opener):
        """A urllib.error.URLError (e.g. connection refused) returns False."""
        alert = _make_alert(AlertChannel.WEBHOOK, webhook_url="http://8.8.8.8/hook")
        event = _make_event()

        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.URLError("connection refused")
        mock_build_opener.return_value = mock_opener

        result = deliver_webhook(alert, event)

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


# ------------------------------------------------------------------
# DNS-rebinding pin (code-review Low security finding)
# ------------------------------------------------------------------


class TestPinnedDelivery:
    """The request-time connection must target the VETTED IP, not a
    fresh DNS resolution (rebinding TOCTOU)."""

    def test_resolve_pinned_ip_passes_through_ip_literal(self):
        from attune.monitoring.validators import resolve_pinned_ip

        assert resolve_pinned_ip("8.8.8.8") == "8.8.8.8"

    def test_resolve_pinned_ip_rejects_private_resolution(self, monkeypatch):
        import socket as socket_mod

        from attune.monitoring import validators

        def fake_getaddrinfo(host, *args, **kwargs):
            return [(socket_mod.AF_INET, socket_mod.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

        monkeypatch.setattr(validators.socket, "getaddrinfo", fake_getaddrinfo)
        with pytest.raises(ValueError, match="unsafe IP"):
            validators.resolve_pinned_ip("rebind.example")

    def test_http_connection_targets_pinned_ip(self, monkeypatch):
        """The socket connects to the pinned IP even though the URL
        names a hostname — proven by capturing the connect target."""
        import socket as socket_mod
        import urllib.request as urlreq

        from attune.monitoring.notifications import _PinnedHTTPHandler

        connected: list[tuple] = []

        def fake_create_connection(addr, *args, **kwargs):
            connected.append(addr)
            raise OSError("stop before real network I/O")

        monkeypatch.setattr(socket_mod, "create_connection", fake_create_connection)
        opener = urlreq.build_opener(_PinnedHTTPHandler("8.8.8.8"))
        with pytest.raises(urllib.error.URLError):
            opener.open("http://webhook.example/hook", timeout=1)

        assert connected == [("8.8.8.8", 80)]

    def test_https_connection_targets_pinned_ip_with_original_sni(self, monkeypatch):
        """HTTPS variant: TCP connects to the pinned IP, but TLS still
        verifies against the ORIGINAL hostname (SNI unchanged) — the
        property that keeps pinning from weakening cert validation."""
        import socket as socket_mod
        import urllib.request as urlreq

        from attune.monitoring.notifications import _PinnedHTTPSHandler

        connected: list[tuple] = []
        wrapped: dict[str, str] = {}

        class _FakeSock:
            def close(self):
                pass

        def fake_create_connection(addr, *args, **kwargs):
            connected.append(addr)
            return _FakeSock()

        def fake_wrap_socket(self, sock, server_hostname=None, **kwargs):
            wrapped["server_hostname"] = server_hostname
            raise OSError("stop before real TLS I/O")

        monkeypatch.setattr(socket_mod, "create_connection", fake_create_connection)
        monkeypatch.setattr(ssl.SSLContext, "wrap_socket", fake_wrap_socket)

        opener = urlreq.build_opener(_PinnedHTTPSHandler("8.8.8.8"))
        with pytest.raises(urllib.error.URLError):
            opener.open("https://webhook.example/hook", timeout=1)

        assert connected == [("8.8.8.8", 443)]
        # SNI/cert verification target is the hostname, NOT the pinned IP.
        assert wrapped["server_hostname"] == "webhook.example"

    def test_resolve_pinned_ip_raises_when_resolution_is_empty(self, monkeypatch):
        """Defensive branch: getaddrinfo returning no records."""
        from attune.monitoring import validators

        monkeypatch.setattr(validators, "_resolve_and_check_ip", lambda host: [])
        with pytest.raises(ValueError, match="Cannot resolve hostname"):
            validators.resolve_pinned_ip("empty.example")

    def test_resolve_pinned_ip_returns_first_vetted_ip(self, monkeypatch):
        import socket as socket_mod

        from attune.monitoring import validators

        def fake_getaddrinfo(host, *args, **kwargs):
            return [
                (socket_mod.AF_INET, socket_mod.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
                (socket_mod.AF_INET, socket_mod.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
            ]

        monkeypatch.setattr(validators.socket, "getaddrinfo", fake_getaddrinfo)
        assert validators.resolve_pinned_ip("public.example") == "93.184.216.34"
