"""Response caching for Attune AI workflows.

Provides hybrid hash + semantic similarity caching to reduce API costs by 70%.

Usage:
    from attune.cache import create_cache

    # Auto-detect best cache (hybrid if deps available, hash-only otherwise)
    cache = create_cache()

    # Manual cache selection
    from attune.cache import HashOnlyCache, HybridCache

    cache = HashOnlyCache()  # Always available
    cache = HybridCache()    # Requires sentence-transformers

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from typing import Optional

from .base import BaseCache, CacheEntry, CacheStats
from .hash_only import HashOnlyCache

logger = logging.getLogger(__name__)

# Try to import HybridCache (requires optional dependencies)
try:
    from .hybrid import HybridCache

    HYBRID_AVAILABLE = True
except ImportError:
    HYBRID_AVAILABLE = False
    HybridCache = None  # type: ignore


def create_cache(
    cache_type: str | None = None,
    **kwargs,
) -> BaseCache:
    """Create appropriate cache based on available dependencies.

    Auto-detects if sentence-transformers is available and creates
    HybridCache if possible, otherwise falls back to HashOnlyCache.

    Args:
        cache_type: Force specific cache type ("hash" | "hybrid" | None for auto).
        **kwargs: Additional arguments passed to cache constructor.

    Returns:
        BaseCache instance (HybridCache or HashOnlyCache).

    Example:
        # Auto-detect (recommended)
        cache = create_cache()

        # Force hash-only
        cache = create_cache(cache_type="hash")

        # Force hybrid (raises ImportError if deps missing)
        cache = create_cache(cache_type="hybrid")

    """
    # Force hash-only
    if cache_type == "hash":
        logger.info("Using hash-only cache (explicit)")
        return HashOnlyCache(**kwargs)

    # Force hybrid
    if cache_type == "hybrid":
        if not HYBRID_AVAILABLE:
            raise ImportError(
                "HybridCache requires sentence-transformers. "
                "Install with: pip install attune-ai[cache]"
            )
        logger.info("Using hybrid cache (explicit)")
        return HybridCache(**kwargs)

    # Auto-detect (default)
    if HYBRID_AVAILABLE:
        try:
            import sentence_transformers  # noqa: F401

            logger.info("Using hybrid cache (auto-detected)")
            return HybridCache(**kwargs)
        except ImportError:
            logger.info(
                "Using hash-only cache (sentence-transformers not installed). "
                "For 70% cost savings, install with: pip install attune-ai[cache]"
            )
            return HashOnlyCache(**kwargs)

    logger.info(
        "Using hash-only cache (numpy not available). "
        "For 70% cost savings, install with: pip install attune-ai[cache]"
    )
    return HashOnlyCache(**kwargs)


def auto_setup_cache() -> None:
    """Auto-setup cache with one-time prompt if dependencies missing.

    Called automatically by BaseWorkflow on first run.
    Prompts user to install cache dependencies if not available.

    """
    from .dependency_manager import DependencyManager

    manager = DependencyManager()

    if manager.should_prompt_cache_install():
        manager.prompt_cache_install()


__all__ = [
    "BaseCache",
    "CacheEntry",
    "CacheStats",
    "HashOnlyCache",
    "HybridCache",
    "create_cache",
    "auto_setup_cache",
    "HYBRID_AVAILABLE",
]
