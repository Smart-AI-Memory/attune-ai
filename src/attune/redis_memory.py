"""Redis Short-Term Memory for Attune AI

Per EMPATHY_PHILOSOPHY.md v1.1.0:
- Implements fast, TTL-based working memory for agent coordination
- Role-based access tiers for data integrity
- Pattern staging before validation
- Principled negotiation support

This module serves as the public API facade. The implementation
is split across focused modules:
- redis_memory_models: Data models (TTLStrategy, AgentCredentials,
  StagedPattern, ConflictContext)
- redis_memory_storage: Core storage engine and working memory
- redis_memory_patterns: Pattern staging workflow
- redis_memory_coordination: Conflict negotiation, coordination
  signals, and session management

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

# Re-export all public models
# Import implementation components
from .redis_memory_coordination import (
    ConflictNegotiationMixin,
    CoordinationSignalsMixin,
    SessionManagementMixin,
)
from .redis_memory_models import (  # noqa: F401 - re-exported
    AccessTier,
    AgentCredentials,
    ConflictContext,
    StagedPattern,
    TTLStrategy,
)
from .redis_memory_patterns import PatternStagingMixin
from .redis_memory_storage import RedisStorageBase


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
    "RedisShortTermMemory",
    "StagedPattern",
    "TTLStrategy",
]
