"""Tests for SSRF hardening in webhook validation and delivery.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import socket
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from attune.monitoring.validators import (
    _resolve_and_check_ip,
    _validate_webhook_url,
)

# ---------------------------------------------------------------------------
# Regression tests for existing SSRF prevention
# ---------------------------------------------------------------------------


class TestValidateWebhookUrlExistingChecks:
    """Regression tests for existing SSRF prevention."""

    def test_blocks_localhost_hostname(self):
        with pytest.raises(ValueError, match="local or metadata"):
            _validate_webhook_url("http://localhost/hook")

    def test_blocks_loopback_ip(self):
        # 127.0.0.1 is in blocked_hosts set, caught as "local or metadata"
        with pytest.raises(ValueError, match="local or metadata"):
            _validate_webhook_url("http://127.0.0.1/hook")

    def test_blocks_private_ip_10(self):
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://10.0.0.1/hook")

    def test_blocks_private_ip_172(self):
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://172.16.0.1/hook")

    def test_blocks_private_ip_192(self):
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://192.168.1.1/hook")

    def test_blocks_link_local_ip(self):
        with pytest.raises(ValueError, match="link-local"):
            _validate_webhook_url("http://169.254.1.1/hook")

    def test_blocks_metadata_service(self):
        with pytest.raises(ValueError, match="local or metadata"):
            _validate_webhook_url("http://169.254.169.254/latest/meta-data/")

    def test_blocks_non_http_scheme(self):
        with pytest.raises(ValueError, match="Invalid scheme"):
            _validate_webhook_url("ftp://example.com/hook")

    def test_blocks_internal_service_port_redis(self):
        with pytest.raises(ValueError, match="internal service port"):
            _validate_webhook_url("http://example.com:6379/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_allows_valid_https_url(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        result = _validate_webhook_url("https://hooks.slack.com/services/T0/B0/x")
        assert result == "https://hooks.slack.com/services/T0/B0/x"

    def test_blocks_empty_url(self):
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_webhook_url("")

    def test_blocks_none_url(self):
        with pytest.raises(ValueError, match="non-empty string"):
            _validate_webhook_url(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DNS resolution checks (new)
# ---------------------------------------------------------------------------


class TestDNSResolutionChecks:
    """Tests for DNS resolution SSRF prevention."""

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_blocks_hostname_resolving_to_loopback(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_loopback"):
            _validate_webhook_url("http://evil.example.test/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_blocks_hostname_resolving_to_private_ip(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_private"):
            _validate_webhook_url("http://evil.example.test/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_blocks_hostname_resolving_to_multicast(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("224.0.0.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_multicast"):
            _validate_webhook_url("http://evil.example.test/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_blocks_hostname_resolving_to_link_local(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.1.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_link_local"):
            _validate_webhook_url("http://evil.example.test/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_blocks_unresolvable_hostname(self, mock_dns):
        mock_dns.side_effect = socket.gaierror("Name resolution failed")
        with pytest.raises(ValueError, match="Cannot resolve"):
            _validate_webhook_url("http://nonexistent.example.test/hook")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_allows_hostname_resolving_to_public_ip(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        result = _validate_webhook_url("http://example.com/hook")
        assert result == "http://example.com/hook"


# ---------------------------------------------------------------------------
# Multicast / unspecified IP literal checks (new)
# ---------------------------------------------------------------------------


class TestMulticastUnspecifiedIPLiterals:
    """Tests for multicast and unspecified IP literal checks."""

    def test_blocks_multicast_ip_literal(self):
        with pytest.raises(ValueError, match="multicast"):
            _validate_webhook_url("http://224.0.0.1/hook")

    def test_blocks_unspecified_ip_literal(self):
        # 0.0.0.0 is in the blocked_hosts set
        with pytest.raises(ValueError):
            _validate_webhook_url("http://0.0.0.0/hook")  # nosec B104


# ---------------------------------------------------------------------------
# Direct tests for _resolve_and_check_ip helper
# ---------------------------------------------------------------------------


class TestResolveAndCheckIp:
    """Direct tests for _resolve_and_check_ip helper."""

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_raises_on_gaierror(self, mock_dns):
        mock_dns.side_effect = socket.gaierror("fail")
        with pytest.raises(ValueError, match="Cannot resolve"):
            _resolve_and_check_ip("bad.host")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_raises_on_private_ip(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_private"):
            _resolve_and_check_ip("internal.host")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_passes_on_public_ip(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        _resolve_and_check_ip("dns.google")  # Should not raise

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_checks_all_resolved_ips(self, mock_dns):
        """If any resolved IP is unsafe, the whole hostname is blocked."""
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]
        with pytest.raises(ValueError, match="is_loopback"):
            _resolve_and_check_ip("dual.host")

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_raises_on_unspecified_ip(self, mock_dns):
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("0.0.0.0", 0)),
        ]
        with pytest.raises(ValueError, match="is_unspecified"):
            _resolve_and_check_ip("zero.host")


# ---------------------------------------------------------------------------
# Redirect-blocking in deliver_webhook (new)
# ---------------------------------------------------------------------------


class TestDeliverWebhookRedirect:
    """Tests for redirect-blocking in deliver_webhook."""

    def _make_alert_and_event(self):
        from attune.monitoring.models import (
            AlertChannel,
            AlertConfig,
            AlertEvent,
            AlertMetric,
            AlertSeverity,
        )

        alert = AlertConfig(
            alert_id="test-alert",
            name="Test Alert",
            metric=AlertMetric.DAILY_COST,
            threshold=100.0,
            channel=AlertChannel.WEBHOOK,
            webhook_url="https://hooks.example.com/test",
        )
        event = AlertEvent(
            alert_id="test-alert",
            alert_name="Test Alert",
            metric=AlertMetric.DAILY_COST,
            current_value=150.0,
            threshold=100.0,
            severity=AlertSeverity.WARNING,
            triggered_at=datetime.now(timezone.utc),
            message="Test alert triggered",
        )
        return alert, event

    @patch("attune.monitoring.notifications.logger")
    @patch("attune.monitoring.validators.socket.getaddrinfo")
    @patch("attune.monitoring.notifications.build_opener")
    def test_blocks_302_redirect(self, mock_build_opener, mock_dns, _mock_log):
        import urllib.error

        from attune.monitoring.notifications import deliver_webhook

        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError(
            "http://127.0.0.1/admin",
            302,
            "Redirect blocked",
            {},
            None,
        )
        mock_build_opener.return_value = mock_opener

        alert, event = self._make_alert_and_event()
        result = deliver_webhook(alert, event)
        assert result is False

    @patch("attune.monitoring.notifications.logger")
    @patch("attune.monitoring.validators.socket.getaddrinfo")
    @patch("attune.monitoring.notifications.build_opener")
    def test_blocks_301_redirect(self, mock_build_opener, mock_dns, _mock_log):
        import urllib.error

        from attune.monitoring.notifications import deliver_webhook

        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.HTTPError(
            "http://internal.host/",
            301,
            "Redirect blocked",
            {},
            None,
        )
        mock_build_opener.return_value = mock_opener

        alert, event = self._make_alert_and_event()
        result = deliver_webhook(alert, event)
        assert result is False

    @patch("attune.monitoring.notifications.logger")
    @patch("attune.monitoring.validators.socket.getaddrinfo")
    @patch("attune.monitoring.notifications.build_opener")
    def test_delivers_200_successfully(self, mock_build_opener, mock_dns, _mock_log):
        from attune.monitoring.notifications import deliver_webhook

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

        alert, event = self._make_alert_and_event()
        result = deliver_webhook(alert, event)
        assert result is True

    @patch("attune.monitoring.notifications.logger")
    @patch("attune.monitoring.validators.socket.getaddrinfo")
    @patch("attune.monitoring.notifications.build_opener")
    def test_delivers_slack_webhook_format(self, mock_build_opener, mock_dns, _mock_log):
        from attune.monitoring.notifications import deliver_webhook

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

        alert, event = self._make_alert_and_event()
        alert.webhook_url = "https://hooks.slack.com/services/T0/B0/x"
        result = deliver_webhook(alert, event)
        assert result is True
