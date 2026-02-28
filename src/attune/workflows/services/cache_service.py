"""Cache service for workflows.

Standalone service extracted from CachingMixin. Provides LLM response caching
with automatic setup and graceful degradation.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..caching import CachedResponse

if TYPE_CHECKING:
    from attune.cache import BaseCache

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching LLM responses.

    Manages cache lifecycle (setup, lookup, store) with graceful degradation
    when cache backends are unavailable.

    Args:
        workflow_name: Name of the workflow using this cache
        cache: Optional pre-configured cache instance
        enable: Whether caching is enabled (default True)

    Example:
        >>> cache_svc = CacheService("code-review")
        >>> cached = cache_svc.lookup("stage1", system_prompt, user_msg, model)
        >>> if cached is None:
        ...     # call LLM, then store
        ...     cache_svc.store("stage1", system_prompt, user_msg, model, response)

    """

    def __init__(
        self,
        workflow_name: str,
        cache: BaseCache | None = None,
        enable: bool = True,
    ) -> None:
        self._workflow_name = workflow_name
        self._cache: BaseCache | None = cache
        self._enable: bool = enable
        self._setup_attempted: bool = cache is not None

    @property
    def enabled(self) -> bool:
        """Whether caching is currently enabled."""
        return self._enable

    def setup(self) -> None:
        """Set up cache with one-time auto-configuration if needed.

        This is called lazily on first use to avoid blocking initialization.
        """
        if not self._enable or self._setup_attempted:
            return

        self._setup_attempted = True

        if self._cache is not None:
            return

        from attune.cache import auto_setup_cache, create_cache

        try:
            auto_setup_cache()
            self._cache = create_cache()
            logger.info(f"Cache initialized for workflow: {self._workflow_name}")
        except ImportError as e:
            logger.info(
                f"Using hash-only cache (install attune-ai[cache] for semantic caching): {e}",
            )
            self._cache = create_cache(cache_type="hash")
        except (OSError, PermissionError) as e:
            logger.warning(f"Cache setup failed (file system error): {e}, continuing without cache")
            self._enable = False
        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"Cache setup failed (config error): {e}, continuing without cache")
            self._enable = False

    def make_key(self, system: str, user_message: str) -> str:
        """Create cache key from system and user prompts.

        Args:
            system: System prompt
            user_message: User message

        Returns:
            Combined prompt string for cache key

        """
        return f"{system}\n\n{user_message}" if system else user_message

    def lookup(
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
        if not self._enable or self._cache is None:
            return None

        try:
            full_prompt = self.make_key(system, user_message)
            cached_data = self._cache.get(self._workflow_name, stage, full_prompt, model)

            if cached_data is not None:
                logger.debug(f"Cache hit for {self._workflow_name}:{stage}")
                return CachedResponse.from_dict(cached_data)

        except (KeyError, TypeError, ValueError) as e:
            logger.debug(f"Cache lookup failed (malformed data): {e}")
        except (OSError, PermissionError) as e:
            logger.debug(f"Cache lookup failed (file system error): {e}")

        return None

    def store(
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
        if not self._enable or self._cache is None:
            return False

        try:
            full_prompt = self.make_key(system, user_message)
            self._cache.put(self._workflow_name, stage, full_prompt, model, response.to_dict())
            logger.debug(f"Cached response for {self._workflow_name}:{stage}")
            return True
        except (OSError, PermissionError) as e:
            logger.debug(f"Failed to cache response (file system error): {e}")
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Failed to cache response (serialization error): {e}")

        return False

    def get_cache_type(self) -> str:
        """Get the cache type for telemetry tracking.

        Returns:
            Cache type string (e.g., "hash", "semantic", "none")

        """
        if self._cache is None:
            return "none"

        if hasattr(self._cache, "cache_type"):
            ct = self._cache.cache_type
            return str(ct) if ct and isinstance(ct, str) else "hash"

        return "hash"

    def get_stats(self) -> dict[str, Any]:
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
            logger.debug(f"Cache stats not available: {e}")
            return {"hits": 0, "misses": 0, "hit_rate": 0.0}
