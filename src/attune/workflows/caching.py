"""Caching Mixin for Workflow LLM Calls (No-op)

The custom LLM response cache has been removed in favor of Anthropic's
built-in prompt caching (90% discount on cached input tokens, automatic
in the Claude Agent SDK). This module retains the CachingMixin interface
as no-op stubs so existing workflow classes continue to work.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached LLM response data (retained for interface compatibility)."""

    content: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedResponse:
        """Create from dictionary."""
        return cls(
            content=data["content"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
        )


class CachingMixin:
    """No-op caching mixin.

    Anthropic's built-in prompt caching (available since Dec 2024)
    provides 90% input token discounts automatically via the Claude
    Agent SDK. This mixin retains the interface so callers don't break.
    """

    _cache: None = None
    _enable_cache: bool = False
    _cache_setup_attempted: bool = True
    name: str = "unknown"

    def _maybe_setup_cache(self) -> None:
        """No-op — Anthropic handles caching server-side."""

    def _make_cache_key(self, system: str, user_message: str) -> str:
        """Create cache key (retained for interface compatibility)."""
        return f"{system}\n\n{user_message}" if system else user_message

    def _try_cache_lookup(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
    ) -> None:
        """No-op — always returns None (cache miss)."""
        return None

    def _store_in_cache(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
        response: CachedResponse,
    ) -> bool:
        """No-op — returns False."""
        return False

    def _get_cache_type(self) -> str:
        """Returns 'anthropic' to indicate server-side caching."""
        return "anthropic"

    def _get_cache_stats(self) -> dict[str, Any]:
        """Returns empty stats."""
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}
