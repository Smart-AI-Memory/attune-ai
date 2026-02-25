"""Redis Memory Data Models — Deprecation Shim.

All types have moved to ``attune.memory.types``.
This module re-exports them for backward compatibility.

Migrate imports to::

    from attune.memory.types import AccessTier, TTLStrategy, ...

This shim will be removed when attune-redis is released.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

from .memory.types import (  # noqa: F401 - re-exported
    AccessTier,
    AgentCredentials,
    ConflictContext,
    StagedPattern,
    TTLStrategy,
)

warnings.warn(
    "attune.redis_memory_models is deprecated. " "Import from attune.memory.types instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "AccessTier",
    "AgentCredentials",
    "ConflictContext",
    "StagedPattern",
    "TTLStrategy",
]
