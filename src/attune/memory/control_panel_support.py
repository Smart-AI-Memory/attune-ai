"""Support classes for Memory Control Panel.

Rate limiting, authentication, and statistics tracking.

Copyright 2025 Smart AI Memory, LLC
Licensed under Fair Source 0.9
"""

import hashlib
import hmac
import os
import time
from collections import defaultdict
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter by IP address."""

    def __init__(self, window_seconds: int = 60, max_requests: int = 100):
        """Initialize rate limiter.

        Args:
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed per window

        Raises:
            ValueError: If window_seconds or max_requests is invalid

        """
        if window_seconds < 1:
            raise ValueError(f"window_seconds must be positive, got {window_seconds}")

        if max_requests < 1:
            raise ValueError(f"max_requests must be positive, got {max_requests}")

        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed for this IP.

        Args:
            client_ip: The client IP address

        Returns:
            True if allowed, False if rate limited

        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[client_ip] = [ts for ts in self._requests[client_ip] if ts > window_start]

        # Check if over limit
        if len(self._requests[client_ip]) >= self.max_requests:
            logger.warning("rate_limit_exceeded", client_ip=client_ip)
            return False

        # Record this request
        self._requests[client_ip].append(now)
        return True

    def get_remaining(self, client_ip: str) -> int:
        """Get remaining requests for this IP."""
        now = time.time()
        window_start = now - self.window_seconds
        recent = [ts for ts in self._requests[client_ip] if ts > window_start]
        return max(0, self.max_requests - len(recent))


class APIKeyAuth:
    """Simple API key authentication."""

    def __init__(self, api_key: str | None = None):
        """Initialize API key auth.

        Args:
            api_key: The API key to require. If None, reads from
                     EMPATHY_MEMORY_API_KEY env var. If still None, auth is disabled.

        """
        self.api_key = api_key or os.environ.get("EMPATHY_MEMORY_API_KEY")
        self.enabled = bool(self.api_key)
        self._key_hash: bytes | None = None
        if self.enabled and self.api_key:
            # Store HMAC of API key for secure comparison
            self._key_hash = hmac.new(
                b"empathy-api-key-auth", self.api_key.encode(), "sha256"
            ).digest()
            logger.info("api_key_auth_enabled")
        else:
            logger.info("api_key_auth_disabled", reason="no_key_configured")

    def is_valid(self, provided_key: str | None) -> bool:
        """Check if provided API key is valid.

        Args:
            provided_key: The key provided in the request

        Returns:
            True if valid or auth disabled, False otherwise

        """
        if not self.enabled:
            return True

        if not provided_key:
            return False

        # Constant-time comparison via HMAC
        provided_hash = hmac.new(b"empathy-api-key-auth", provided_key.encode(), "sha256").digest()
        return hmac.compare_digest(provided_hash, self._key_hash)


@dataclass
class MemoryStats:
    """Statistics for memory system."""

    # Redis stats
    redis_available: bool = False
    redis_method: str = "none"
    redis_keys_total: int = 0
    redis_keys_working: int = 0
    redis_keys_staged: int = 0
    redis_memory_used: str = "0"

    # Long-term stats
    long_term_available: bool = False
    patterns_total: int = 0
    patterns_public: int = 0
    patterns_internal: int = 0
    patterns_sensitive: int = 0
    patterns_encrypted: int = 0

    # Performance stats
    redis_ping_ms: float = 0.0
    storage_bytes: int = 0
    collection_time_ms: float = 0.0

    # Timestamps
    collected_at: str = ""
