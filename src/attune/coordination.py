"""Deprecation shim — `attune.coordination` was removed in v6.8.0.

The Redis-backed coordination classes (`AgentCoordinator`, `TeamSession`,
`AgentTask`, `ConflictResolver`, `ResolutionResult`, `ResolutionStrategy`,
`TeamPriorities`) had no internal callers in attune-ai itself, were tightly
coupled to Redis, and were preventing `pip install attune-ai` from being
truly Redis-free.

See `docs/specs/redis-decoupling/` (P1 deliverable) for the audit and
rationale.

This shim raises a helpful `ImportError` on any attribute access. If you
depended on these classes, your options are:

1. Pin `attune-ai<6.8.0` in your install (the v6.7.x line is the last
   release that ships them).
2. Copy the classes from the v6.7.1 source tree into your own project
   — they're standalone Redis-backed helpers with no further attune-ai
   dependency.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

_REMOVED_NAMES = frozenset(
    {
        "AgentCoordinator",
        "AgentTask",
        "ConflictResolver",
        "ResolutionResult",
        "ResolutionStrategy",
        "TeamPriorities",
        "TeamSession",
    }
)

_MESSAGE = (
    "`attune.coordination.{name}` was removed in v6.8.0. "
    "The Redis-backed coordination primitives had no internal callers "
    "in attune-ai itself and were blocking Redis-free installs. "
    "If you depended on them, pin `attune-ai<6.8.0` or copy the "
    "classes from the v6.7.x source tree. "
    "See docs/specs/redis-decoupling/ for context."
)


def __getattr__(name: str) -> object:
    """PEP 562 module-level hook — raise on removed names, else AttributeError."""
    if name in _REMOVED_NAMES:
        raise ImportError(_MESSAGE.format(name=name))
    raise AttributeError(f"module 'attune.coordination' has no attribute {name!r}")
