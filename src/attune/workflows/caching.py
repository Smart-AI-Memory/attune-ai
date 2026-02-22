"""Caching Mixin for Workflow LLM Calls

Extracted from BaseWorkflow to improve maintainability and reusability.
Provides caching behavior for LLM calls with automatic cache setup.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from attune.cache import BaseCache

logger = logging.getLogger(__name__)


@dataclass
class CachedResponse:
    """Cached LLM response data."""

    content: str
    input_tokens: int
    output_tokens: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for cache storage."""
        return {
            "content": self.content,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CachedResponse:
        """Create from dictionary (cache retrieval)."""
        return cls(
            content=data["content"],
            input_tokens=data["input_tokens"],
            output_tokens=data["output_tokens"],
        )


@runtime_checkable
class CacheAwareWorkflow(Protocol):
    """Protocol for workflows that support caching."""

    name: str
    _cache: BaseCache | None
    _enable_cache: bool

    def get_model_for_tier(self, tier: Any) -> str:
        """Get model ID for a given tier."""
        ...


class CachingMixin:
    """Mixin that provides caching behavior for LLM calls.

    This mixin extracts caching logic from BaseWorkflow to improve
    maintainability and enable reuse in other contexts.

    Attributes:
        _cache: Optional cache instance
        _enable_cache: Whether caching is enabled
        _cache_setup_attempted: Whether cache setup has been tried

    Usage:
        class MyWorkflow(CachingMixin, BaseWorkflow):
            pass

        # CachingMixin methods are now available
        workflow._maybe_setup_cache()
        cached = workflow._try_cache_lookup(...)
        workflow._store_in_cache(...)
    """

    # Instance variables (set by __init__ or subclass)
    _cache: BaseCache | None = None
    _enable_cache: bool = True
    _cache_setup_attempted: bool = False

    # These must be provided by the class using this mixin
    name: str = "unknown"

    def _maybe_setup_cache(self) -> None:
        """Set up cache with one-time user prompt if needed.

        This is called lazily on first workflow execution to avoid
        blocking workflow initialization.
        """
        if not self._enable_cache:
            return

        if self._cache_setup_attempted:
            return

        self._cache_setup_attempted = True

        # If cache already provided, use it
        if self._cache is not None:
            return

        # Import here to avoid circular imports
        from attune.cache import auto_setup_cache, create_cache

        # Otherwise, trigger auto-setup (which may prompt user)
        try:
            auto_setup_cache()
            self._cache = create_cache()
            logger.info(f"Cache initialized for workflow: {self.name}")
        except ImportError as e:
            # Hybrid cache dependencies not available, fall back to hash-only
            logger.info(
                f"Using hash-only cache (install attune-ai[cache] for semantic caching): {e}"
            )
            self._cache = create_cache(cache_type="hash")
        except (OSError, PermissionError) as e:
            # File system errors - disable cache
            logger.warning(f"Cache setup failed (file system error): {e}, continuing without cache")
            self._enable_cache = False
        except (ValueError, TypeError, AttributeError) as e:
            # Configuration errors - disable cache
            logger.warning(f"Cache setup failed (config error): {e}, continuing without cache")
            self._enable_cache = False

    def _make_cache_key(self, system: str, user_message: str) -> str:
        """Create cache key from system and user prompts.

        Args:
            system: System prompt
            user_message: User message

        Returns:
            Combined prompt string for cache key
        """
        return f"{system}\n\n{user_message}" if system else user_message

    def _try_cache_lookup(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
    ) -> CachedResponse | None:
        """Try to retrieve a cached response.

        Args:
            stage: Stage name for cache key
            system: System prompt
            user_message: User message
            model: Model ID

        Returns:
            CachedResponse if found, None otherwise
        """
        if not self._enable_cache or self._cache is None:
            return None

        try:
            full_prompt = self._make_cache_key(system, user_message)
            cached_data = self._cache.get(self.name, stage, full_prompt, model)

            if cached_data is not None:
                logger.debug(f"Cache hit for {self.name}:{stage}")
                return CachedResponse.from_dict(cached_data)

        except (KeyError, TypeError, ValueError) as e:
            # Malformed cache data - continue with LLM call
            logger.debug(f"Cache lookup failed (malformed data): {e}, continuing with LLM call")
        except (OSError, PermissionError) as e:
            # File system errors - continue with LLM call
            logger.debug(f"Cache lookup failed (file system error): {e}, continuing with LLM call")

        return None

    def _store_in_cache(
        self,
        stage: str,
        system: str,
        user_message: str,
        model: str,
        response: CachedResponse,
    ) -> bool:
        """Store a response in the cache.

        Args:
            stage: Stage name for cache key
            system: System prompt
            user_message: User message
            model: Model ID
            response: Response to cache

        Returns:
            True if stored successfully, False otherwise
        """
        if not self._enable_cache or self._cache is None:
            return False

        try:
            full_prompt = self._make_cache_key(system, user_message)
            self._cache.put(self.name, stage, full_prompt, model, response.to_dict())
            logger.debug(f"Cached response for {self.name}:{stage}")
            return True
        except (OSError, PermissionError) as e:
            # File system errors - log but continue
            logger.debug(f"Failed to cache response (file system error): {e}")
        except (ValueError, TypeError, KeyError) as e:
            # Data serialization errors - log but continue
            logger.debug(f"Failed to cache response (serialization error): {e}")

        return False

    def _get_cache_type(self) -> str:
        """Get the cache type for telemetry tracking.

        Returns:
            Cache type string (e.g., "hash", "semantic")
        """
        if self._cache is None:
            return "none"

        if hasattr(self._cache, "cache_type"):
            ct = self._cache.cache_type
            # Ensure it's a string (not a Mock object)
            return str(ct) if ct and isinstance(ct, str) else "hash"

        return "hash"  # Default assumption

    def _get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for cost reporting.

        Returns:
            Dictionary with cache stats (hits, misses, hit_rate)
        """
        if self._cache is None:
            return {"hits": 0, "misses": 0, "hit_rate": 0.0}

        try:
            stats = self._cache.get_stats()
            return {
                "hits": stats.hits,
                "misses": stats.misses,
                "hit_rate": stats.hit_rate,
            }
        except (AttributeError, TypeError) as e:
            # Cache doesn't support stats
            logger.debug(f"Cache stats not available: {e}")
            return {"hits": 0, "misses": 0, "hit_rate": 0.0}
