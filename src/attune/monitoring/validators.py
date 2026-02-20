"""Webhook URL validation for SSRF prevention.

Validates webhook URLs to prevent Server-Side Request Forgery
(SSRF) attacks by blocking unsafe destinations including localhost,
private IPs, cloud metadata services, and internal service ports.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ipaddress
import urllib.parse


def _validate_webhook_url(url: str) -> str:
    """Validate webhook URL to prevent SSRF attacks.

    Args:
        url: Webhook URL to validate

    Returns:
        Validated URL (unchanged if valid)

    Raises:
        ValueError: If URL is invalid or targets unsafe destinations

    Security:
        Prevents Server-Side Request Forgery (SSRF) by blocking:
        - Non-HTTP(S) schemes (file://, gopher://, ftp://)
        - Localhost and loopback addresses (127.0.0.1, ::1)
        - Cloud metadata services (169.254.169.254)
        - Private IP ranges (10.x, 172.16-31.x, 192.168.x)
        - Common internal service ports (Redis, PostgreSQL, etc.)
    """
    if not url or not isinstance(url, str):
        raise ValueError("webhook_url must be a non-empty string")

    # Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid scheme '{parsed.scheme}'. Only http and https allowed for webhooks."
        )

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL must contain a valid hostname")

    # Blocked hostnames (localhost, metadata services)
    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # nosec B104 - blocklist, not a bind
        "::1",
        "[::1]",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
        "instance-data",  # Azure metadata pattern
    }

    hostname_lower = hostname.lower()
    if hostname_lower in blocked_hosts:
        raise ValueError(f"Webhook URL cannot target local or metadata address: {hostname}")

    # Check for private/internal IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private:
            raise ValueError(f"Webhook URL cannot target private IP: {hostname}")
        if ip.is_loopback:
            raise ValueError(f"Webhook URL cannot target loopback address: {hostname}")
        if ip.is_link_local:
            raise ValueError(f"Webhook URL cannot target link-local address: {hostname}")
        if ip.is_reserved:
            raise ValueError(f"Webhook URL cannot target reserved IP: {hostname}")
    except ValueError as e:
        # Check if this is our own validation error
        if "cannot target" in str(e):
            raise
        # Not an IP address (it's a hostname) - that's fine, continue

    # Block common internal service ports
    if parsed.port is not None:
        blocked_ports = {
            22,  # SSH
            23,  # Telnet
            3306,  # MySQL
            5432,  # PostgreSQL
            6379,  # Redis
            27017,  # MongoDB
            9200,  # Elasticsearch
            2379,  # etcd
            8500,  # Consul
        }
        if parsed.port in blocked_ports:
            raise ValueError(
                f"Webhook URL cannot target internal service port {parsed.port}. "
                "Use standard HTTP (80) or HTTPS (443) ports."
            )

    return url
