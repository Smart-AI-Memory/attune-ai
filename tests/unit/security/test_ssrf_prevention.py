"""Tests for SSRF (Server-Side Request Forgery) prevention (CWE-918).

Verifies that _validate_webhook_url() properly blocks:
- Localhost and loopback addresses
- Private IP ranges
- Cloud metadata service endpoints
- Non-HTTP schemes (file://, gopher://)
- Internal service ports

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import socket
from unittest.mock import patch

import pytest

from attune.monitoring.alerts import _validate_webhook_url


class TestSSRFPrevention:
    """Test suite for SSRF attack prevention in webhook URLs."""

    def test_blocks_localhost(self):
        """Test that localhost URLs are blocked."""
        localhost_urls = [
            "http://localhost",
            "http://localhost:8080",
            "http://localhost:6379",
            "https://localhost/webhook",
        ]

        for url in localhost_urls:
            with pytest.raises(ValueError, match="local"):
                _validate_webhook_url(url)

    def test_blocks_loopback_ipv4(self):
        """Test that IPv4 loopback addresses are blocked."""
        loopback_urls = [
            "http://127.0.0.1",
            "http://127.0.0.1:8080",
            "http://127.0.0.1/api/webhook",
            "http://0.0.0.0:5000",
        ]

        for url in loopback_urls:
            with pytest.raises(ValueError):
                _validate_webhook_url(url)

    def test_blocks_loopback_ipv6(self):
        """Test that IPv6 loopback addresses are blocked."""
        loopback_urls = [
            "http://[::1]",
            "http://[::1]:8080",
        ]

        for url in loopback_urls:
            with pytest.raises(ValueError):
                _validate_webhook_url(url)

    def test_blocks_aws_metadata(self):
        """Test that AWS metadata service is blocked."""
        metadata_urls = [
            "http://169.254.169.254",
            "http://169.254.169.254/latest/meta-data",
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        ]

        for url in metadata_urls:
            with pytest.raises(ValueError, match="metadata|local"):
                _validate_webhook_url(url)

    def test_blocks_gcp_metadata(self):
        """Test that GCP metadata service is blocked."""
        with pytest.raises(ValueError, match="metadata"):
            _validate_webhook_url("http://metadata.google.internal/computeMetadata/v1/")

    def test_blocks_non_http_schemes(self):
        """Test that non-HTTP(S) schemes are blocked."""
        dangerous_schemes = [
            "file:///etc/passwd",
            "ftp://internal-server/data",
            "gopher://localhost:6379/_GET%20secret",
            "dict://localhost:11211/stats",
            "ldap://localhost:389/dc=example,dc=com",
        ]

        for url in dangerous_schemes:
            with pytest.raises(ValueError, match="scheme"):
                _validate_webhook_url(url)

    def test_blocks_internal_service_ports(self):
        """Test that common internal service ports are blocked."""
        internal_ports = [
            ("http://internal-db:3306", "MySQL"),
            ("http://redis-cache:6379", "Redis"),
            ("http://mongo:27017", "MongoDB"),
            ("http://elasticsearch:9200", "Elasticsearch"),
            ("http://postgres:5432", "PostgreSQL"),
            ("http://ssh-server:22", "SSH"),
        ]

        for url, _service_name in internal_ports:
            with pytest.raises(ValueError, match="port"):
                _validate_webhook_url(url)

    @patch("attune.monitoring.validators.socket.getaddrinfo")
    def test_allows_valid_webhooks(self, mock_dns):
        """Test that legitimate webhook URLs are allowed."""
        mock_dns.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]
        valid_urls = [
            "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
            "https://discord.com/api/webhooks/123456789/abcdef",
            "https://api.pagerduty.com/v2/events",
            "https://example.com/webhook",
            "http://external-api.example.com:443/callback",
        ]

        for url in valid_urls:
            result = _validate_webhook_url(url)
            assert result == url

    def test_blocks_empty_url(self):
        """Test that empty URLs are rejected."""
        with pytest.raises(ValueError, match="non-empty"):
            _validate_webhook_url("")

        with pytest.raises(ValueError, match="non-empty"):
            _validate_webhook_url(None)

    def test_blocks_url_without_hostname(self):
        """Test that URLs without hostname are rejected."""
        with pytest.raises(ValueError, match="hostname"):
            _validate_webhook_url("http:///path")


class TestPrivateIPBlocking:
    """Test that private IP ranges are blocked."""

    def test_blocks_class_a_private(self):
        """Test that 10.x.x.x private range is blocked."""
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://10.0.0.1/webhook")

    def test_blocks_class_b_private(self):
        """Test that 172.16-31.x.x private range is blocked."""
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://172.16.0.1/webhook")

    def test_blocks_class_c_private(self):
        """Test that 192.168.x.x private range is blocked."""
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url("http://192.168.1.1/webhook")

    def test_blocks_link_local(self):
        """Test that link-local addresses (169.254.x.x) are blocked."""
        with pytest.raises(ValueError):
            _validate_webhook_url("http://169.254.1.1/webhook")


class TestSSRFBypassPrevention:
    """Test that SSRF bypass techniques are blocked."""

    def test_blocks_url_encoded_localhost(self):
        """Test that URL-encoded localhost (127.0.0.1) is blocked."""
        encoded_urls = [
            "http://%31%32%37%2e%30%2e%30%2e%31/",  # 127.0.0.1
            "http://%6c%6f%63%61%6c%68%6f%73%74/",  # localhost
        ]
        for url in encoded_urls:
            with pytest.raises(ValueError):
                _validate_webhook_url(url)

    def test_blocks_url_encoded_metadata(self):
        """Test that URL-encoded metadata IP is blocked."""
        # 169.254.169.254 URL-encoded
        url = "http://%31%36%39%2e%32%35%34%2e%31%36%39%2e%32%35%34/latest/"
        with pytest.raises(ValueError):
            _validate_webhook_url(url)

    def test_blocks_ipv6_zone_id_bypass(self):
        """Test that IPv6 zone ID cannot bypass loopback check."""
        zone_id_urls = [
            "http://[::1%25eth0]/",
            "http://[fe80::1%25lo]/",
        ]
        for url in zone_id_urls:
            with pytest.raises(ValueError):
                _validate_webhook_url(url)

    def test_blocks_url_encoded_private_ip(self):
        """Test that URL-encoded private IPs are blocked."""
        # 10.0.0.1 URL-encoded
        url = "http://%31%30%2e%30%2e%30%2e%31/webhook"
        with pytest.raises(ValueError, match="private"):
            _validate_webhook_url(url)
