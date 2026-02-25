"""Deprecated — use attune_redis.AMSMemoryBackend.

REMOVE IN v4.0.0 — see docs/migration/redis-plugin-migration.md

Legacy facade for RedisShortTermMemory. Kept for backward
compatibility. New code should use the ``attune_redis``
plugin package.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune.redis_memory is deprecated. " "Use attune_redis.AMSMemoryBackend instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export types for backward compat
from .memory.types import (  # noqa: E402, F401
    AccessTier,
    AgentCredentials,
    ConflictContext,
    StagedPattern,
    TTLStrategy,
)
from .redis_memory_coordination import (  # noqa: E402
    ConflictNegotiationMixin,
    CoordinationSignalsMixin,
    SessionManagementMixin,
)
from .redis_memory_patterns import PatternStagingMixin  # noqa: E402
from .redis_memory_storage import REDIS_AVAILABLE, RedisStorageBase  # noqa: E402, F401


class RedisShortTermMemory(
    PatternStagingMixin,
    ConflictNegotiationMixin,
    CoordinationSignalsMixin,
    SessionManagementMixin,
    RedisStorageBase,
):
    """Redis-backed short-term memory for agent coordination

    Features:
    - Fast read/write with automatic TTL expiration
    - Role-based access control
    - Pattern staging workflow
    - Conflict negotiation context
    - Agent working memory

    Example:
        >>> memory = RedisShortTermMemory()
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> memory.stash("analysis_results", {"issues": 3}, creds)
        >>> data = memory.retrieve("analysis_results", creds)

    """

    pass


__all__ = [
    "AccessTier",
    "AgentCredentials",
    "ConflictContext",
    "REDIS_AVAILABLE",
    "RedisShortTermMemory",
    "StagedPattern",
    "TTLStrategy",
]
