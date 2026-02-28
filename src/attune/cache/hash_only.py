"""Hash-only cache implementation using SHA256 for exact matching.

Provides fast exact-match caching with ~30% hit rate. No dependencies required.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import heapq
import logging
import time
from typing import Any

from .base import BaseCache, CacheEntry, CacheStats

logger = logging.getLogger(__name__)


class HashOnlyCache(BaseCache):
    """Fast hash-based cache for exact prompt matches.

    Uses SHA256 hashing for O(1) lookup. Provides ~30% cache hit rate
    for workflows with repeated exact prompts (e.g., re-reviewing same code).

    No external dependencies required - always available as fallback.

    Example:
        cache = HashOnlyCache()

        # First call (miss)
        result = cache.get("code-review", "scan", prompt, "claude-3-5-sonnet")
        # → None

        # Store response
        cache.put("code-review", "scan", prompt, "claude-3-5-sonnet", response)

        # Second call with exact same prompt (hit)
        result = cache.get("code-review", "scan", prompt, "claude-3-5-sonnet")
        # → response (from cache, <5μs lookup)

    """

    def __init__(
        self,
        max_size_mb: int = 500,
        default_ttl: int = 86400,
        max_memory_mb: int = 100,
    ):
        """Initialize hash-only cache.

        Args:
            max_size_mb: Maximum disk cache size in MB.
            default_ttl: Default TTL in seconds (24 hours).
            max_memory_mb: Maximum in-memory cache size in MB.

        """
        super().__init__(max_size_mb, default_ttl)
        self.max_memory_mb = max_memory_mb
        self._memory_cache: dict[str, CacheEntry] = {}
        self._access_times: dict[str, float] = {}  # For LRU eviction

        logger.debug(
            f"HashOnlyCache initialized (max_memory: {max_memory_mb}MB, "
            f"max_disk: {max_size_mb}MB, ttl: {default_ttl}s)",
        )

    def get(
        self,
        workflow: str,
        stage: str,
        prompt: str,
        model: str,
    ) -> Any | None:
        """Get cached response for exact prompt match.

        Args:
            workflow: Workflow name (e.g., "code-review").
            stage: Stage name (e.g., "scan").
            prompt: Exact prompt text.
            model: Model identifier.

        Returns:
            Cached response if exact match found and not expired, None otherwise.

        """
        cache_key = self._create_cache_key(workflow, stage, prompt, model)

        # Check in-memory cache
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]

            # Check if expired
            current_time = time.time()
            if entry.is_expired(current_time):
                logger.debug(f"Cache entry expired: {cache_key[:16]}...")
                self._evict_entry(cache_key)
                self.stats.misses += 1
                return None

            # Cache hit!
            self._access_times[cache_key] = current_time
            self.stats.hits += 1
            logger.debug(
                f"Cache HIT (hash): {workflow}/{stage} "
                f"(key: {cache_key[:16]}..., hit_rate: {self.stats.hit_rate:.1f}%)",
            )
            return entry.response

        # Cache miss
        self.stats.misses += 1
        logger.debug(
            f"Cache MISS (hash): {workflow}/{stage} "
            f"(key: {cache_key[:16]}..., hit_rate: {self.stats.hit_rate:.1f}%)",
        )
        return None

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
        cache_key = self._create_cache_key(workflow, stage, prompt, model)
        prompt_hash = self._create_cache_key("", "", prompt, "")  # Hash of prompt only

        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            response=response,
            workflow=workflow,
            stage=stage,
            model=model,
            prompt_hash=prompt_hash,
            timestamp=time.time(),
            ttl=ttl or self.default_ttl,
        )

        # Check if we need to evict entries
        self._maybe_evict_lru()

        # Store in memory
        self._memory_cache[cache_key] = entry
        self._access_times[cache_key] = entry.timestamp

        logger.debug(
            f"Cache PUT: {workflow}/{stage} (key: {cache_key[:16]}..., "
            f"entries: {len(self._memory_cache)})",
        )

    def clear(self) -> None:
        """Clear all cached entries."""
        count = len(self._memory_cache)
        self._memory_cache.clear()
        self._access_times.clear()
        logger.info(f"Cache cleared ({count} entries removed)")

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with hit/miss/eviction counts.

        """
        return self.stats

    def _evict_entry(self, cache_key: str) -> None:
        """Remove entry from cache.

        Args:
            cache_key: Key to evict.

        """
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
        if cache_key in self._access_times:
            del self._access_times[cache_key]
        self.stats.evictions += 1

    def _maybe_evict_lru(self) -> None:
        """Evict least recently used entries if cache is too large.

        Uses LRU (Least Recently Used) eviction policy.

        """
        # Estimate memory usage (rough)
        estimated_mb = len(self._memory_cache) * 0.01  # Rough estimate: 10KB per entry

        if estimated_mb > self.max_memory_mb:
            # Evict 10% of entries (LRU)
            num_to_evict = max(1, len(self._memory_cache) // 10)

            # Get oldest entries by access time (LRU eviction)
            oldest_keys = heapq.nsmallest(
                num_to_evict,
                self._access_times.items(),
                key=lambda x: x[1],
            )

            for cache_key, _ in oldest_keys:
                self._evict_entry(cache_key)
                logger.debug(f"LRU eviction: {cache_key[:16]}...")

            logger.info(
                f"LRU eviction: removed {num_to_evict} entries "
                f"(cache size: {len(self._memory_cache)} entries)",
            )

    def evict_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries evicted.

        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._memory_cache.items() if entry.is_expired(current_time)
        ]

        for key in expired_keys:
            self._evict_entry(key)

        if expired_keys:
            logger.info(f"Expired eviction: removed {len(expired_keys)} entries")

        return len(expired_keys)

    def size_info(self) -> dict[str, Any]:
        """Get cache size information.

        Returns:
            Dictionary with cache size metrics.

        """
        return {
            "entries": len(self._memory_cache),
            "estimated_mb": len(self._memory_cache) * 0.01,
            "max_memory_mb": self.max_memory_mb,
        }
