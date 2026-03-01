"""Base cache interface for Attune AI response caching.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Cached LLM response with metadata."""

    key: str
    response: Any
    workflow: str
    stage: str
    model: str
    prompt_hash: str
    timestamp: float
    ttl: int | None = None  # Time-to-live in seconds

    def is_expired(self, current_time: float) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (current_time - self.timestamp) > self.ttl


@dataclass
class CacheStats:
    """Cache hit/miss statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def total(self) -> int:
        """Total cache lookups."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.hits / self.total) * 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "total": self.total,
            "hit_rate": round(self.hit_rate, 1),
        }


class BaseCache(ABC):
    """Abstract base class for LLM response caching."""

    def __init__(self, max_size_mb: int = 500, default_ttl: int = 86400):
        """Initialize cache.

        Args:
            max_size_mb: Maximum cache size in megabytes.
            default_ttl: Default time-to-live in seconds (default: 24 hours).

        """
        self.max_size_mb = max_size_mb
        self.default_ttl = default_ttl
        self.stats = CacheStats()

    @abstractmethod
    def get(
        self,
        workflow: str,
        stage: str,
        prompt: str,
        model: str,
    ) -> Any | None:
        """Get cached response.

        Args:
            workflow: Workflow name (e.g., "code-review").
            stage: Stage name (e.g., "scan").
            prompt: Prompt text.
            model: Model identifier (e.g., "claude-3-5-sonnet-20241022").

        Returns:
            Cached response if found, None otherwise.

        """

    @abstractmethod
    def put(
        self,
        workflow: str,
        stage: str,
        prompt: str,
        model: str,
        response: Any,
        ttl: int | None = None,
    ) -> None:
        """Store response in cache.

        Args:
            workflow: Workflow name.
            stage: Stage name.
            prompt: Prompt text.
            model: Model identifier.
            response: LLM response to cache.
            ttl: Optional custom TTL (uses default if None).

        """

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached entries."""

    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with hit/miss counts.

        """

    def _create_cache_key(
        self,
        workflow: str,
        stage: str,
        prompt: str,
        model: str,
    ) -> str:
        """Create cache key from workflow, stage, prompt, and model.

        Uses SHA256 hash of concatenated values.

        Args:
            workflow: Workflow name.
            stage: Stage name.
            prompt: Prompt text.
            model: Model identifier.

        Returns:
            Cache key (SHA256 hash).

        """
        import hashlib

        # Combine all inputs for cache key
        key_parts = [workflow, stage, prompt, model]
        key_string = "|".join(key_parts)

        # SHA256 hash for consistent key length
        return hashlib.sha256(key_string.encode()).hexdigest()
