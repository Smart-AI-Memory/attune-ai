"""Cache service for workflows (No-op).

The custom LLM response cache has been removed in favor of Anthropic's
built-in prompt caching. This module retains the CacheService interface
as no-op stubs for backward compatibility.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

from ..caching import CachedResponse

logger = logging.getLogger(__name__)


class CacheService:
    """No-op cache service.

    Anthropic's built-in prompt caching provides 90% input token
    discounts automatically via the Claude Agent SDK.
    """

    def __init__(
        self,
        workflow_name: str,
        cache: Any | None = None,
        enable: bool = False,
    ) -> None:
        """Initialize CacheService (no-op)."""
        self._workflow_name = workflow_name
        self._cache = None
        self._enable = False
        self._setup_attempted = True

    @property
    def enabled(self) -> bool:
        """Caching is handled by Anthropic server-side."""
        return False

    def setup(self) -> None:
        """No-op."""

    def make_key(self, system: str, user_message: str) -> str:
        """Create cache key (retained for interface compatibility)."""
        return f"{system}\n\n{user_message}" if system else user_message

    def lookup(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
    ) -> None:
        """No-op — always returns None."""
        return None

    def store(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
        response: CachedResponse,
    ) -> bool:
        """No-op — returns False."""
        return False

    def get_cache_type(self) -> str:
        """Returns 'anthropic' to indicate server-side caching."""
        return "anthropic"

    def get_stats(self) -> dict[str, Any]:
        """Returns empty stats."""
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}
