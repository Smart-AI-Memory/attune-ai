"""Webhook URL validation for SSRF prevention.

Validates webhook URLs to prevent Server-Side Request Forgery
(SSRF) attacks by blocking unsafe destinations including localhost,
private IPs, cloud metadata services, and internal service ports.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse


def _resolve_and_check_ip(hostname: str) -> list[str]:
    """Resolve hostname via DNS and reject unsafe IPs.

    Args:
        hostname: The hostname to resolve

    Returns:
        The vetted resolved IPs, in resolver order.

    Raises:
        ValueError: If any resolved IP is private, loopback,
            link-local, reserved, multicast, or unspecified

    """
    try:
        addrinfo = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname '{hostname}': {e}") from e

    vetted: list[str] = []
    for _family, _type, _proto, _canonname, sockaddr in addrinfo:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        for attr in (
            "is_loopback",
            "is_link_local",
            "is_multicast",
            "is_unspecified",
            "is_reserved",
            "is_private",
        ):
            if getattr(ip, attr):
                raise ValueError(f"Webhook URL resolves to unsafe IP {ip_str} ({attr})")
        vetted.append(ip_str)
    return vetted


def resolve_pinned_ip(hostname: str) -> str:
    """Resolve a hostname once and return a vetted IP to pin.

    Closes the DNS-rebinding TOCTOU: callers must CONNECT to the
    returned IP rather than re-resolving the hostname at request
    time (a second resolution could return a private address after
    validation passed).

    Args:
        hostname: Hostname or IP literal from an already-validated URL.

    Returns:
        The IP address to connect to.

    Raises:
        ValueError: If the name doesn't resolve or resolves to any
            unsafe IP.

    """
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        vetted = _resolve_and_check_ip(hostname)
        if not vetted:
            # `from None`: the outer ValueError only signalled
            # "not an IP literal" — unrelated to this failure.
            raise ValueError(f"Cannot resolve hostname '{hostname}'") from None
        return vetted[0]
    # IP literal — already vetted by _validate_webhook_url.
    return hostname


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

    # Decode URL-encoded characters to prevent encoding bypasses
    # (e.g., http://%31%32%37%2e%30%2e%30%2e%31/ → http://127.0.0.1/)
    try:
        decoded_url = urllib.parse.unquote(url)
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: unquote can raise on malformed percent-encoding;
        # catch broadly to give a clear validation error
        raise ValueError(f"Invalid URL encoding: {e}") from e

    # Parse the decoded URL
    try:
        parsed = urllib.parse.urlparse(decoded_url)
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: urlparse can raise on edge-case inputs;
        # catch broadly to give a clear validation error
        raise ValueError(f"Invalid URL format: {e}") from e

    # Only allow http and https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid scheme '{parsed.scheme}'. Only http and https allowed for webhooks.",
        )

    # Check hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Webhook URL must contain a valid hostname")

    # Strip IPv6 zone IDs (e.g., "fe80::1%25eth0" → "fe80::1")
    # Zone IDs can bypass IP validation checks
    if "%" in hostname:
        hostname = hostname.split("%")[0]

    # Blocked hostnames (localhost, metadata services)
    blocked_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",  # noqa: S104  # nosec B104 — blocklist entry, not a bind
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
    # Order: specific checks first, then broad is_private last
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_loopback:
            raise ValueError(f"Webhook URL cannot target loopback address: {hostname}")
        if ip.is_link_local:
            raise ValueError(f"Webhook URL cannot target link-local address: {hostname}")
        if ip.is_multicast:
            raise ValueError(f"Webhook URL cannot target multicast address: {hostname}")
        if ip.is_unspecified:
            raise ValueError(f"Webhook URL cannot target unspecified address: {hostname}")
        if ip.is_reserved:
            raise ValueError(f"Webhook URL cannot target reserved IP: {hostname}")
        if ip.is_private:
            raise ValueError(f"Webhook URL cannot target private IP: {hostname}")
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
                "Use standard HTTP (80) or HTTPS (443) ports.",
            )

    # Resolve hostname and check all resolved IPs
    try:
        ipaddress.ip_address(hostname)
        # Already validated as IP literal above
    except ValueError:
        # It's a hostname — resolve via DNS and check
        _resolve_and_check_ip(hostname)

    return url
