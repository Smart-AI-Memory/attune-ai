"""Multi-Agent Coordination for Distributed Memory Networks

Provides conflict resolution and coordination primitives for multi-agent
systems sharing pattern libraries.

This package is split into focused modules:
- conflict_resolution: Pattern conflict resolution strategies
- agent_coordinator: Redis-backed task distribution and agent management
- team_session: Collaborative session management

All public APIs are re-exported here for backward compatibility.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .agent_coordinator import AgentCoordinator, AgentTask
from .conflict_resolution import (
    ConflictResolver,
    ResolutionResult,
    ResolutionStrategy,
    TeamPriorities,
)
from .team_session import TeamSession

__all__ = [
    "AgentCoordinator",
    "AgentTask",
    "ConflictResolver",
    "ResolutionResult",
    "ResolutionStrategy",
    "TeamPriorities",
    "TeamSession",
]
