"""Cross-session data models, enums, and constants.

Defines the shared types used by cross-session coordination:
- SessionType, ConflictStrategy enums
- SessionInfo, ConflictResult dataclasses
- Redis key constants and timing thresholds
- Agent ID generation utility

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from attune.memory.short_term import AccessTier

# === Constants ===

CHANNEL_SESSIONS = "empathy:sessions"
KEY_ACTIVE_AGENTS = "empathy:active_agents"
KEY_SERVICE_LOCK = "empathy:service_lock"
KEY_SERVICE_HEARTBEAT = "empathy:service_heartbeat"

HEARTBEAT_INTERVAL_SECONDS = 30
STALE_THRESHOLD_SECONDS = 90
SERVICE_LOCK_TTL_SECONDS = 60


class SessionType(Enum):
    """Type of session/agent."""

    CLAUDE = "claude"  # Interactive Claude Code session
    SERVICE = "service"  # Background service/daemon
    WORKER = "worker"  # Task worker agent


class ConflictStrategy(Enum):
    """Strategy for resolving conflicts between agents."""

    PRIORITY_BASED = "priority"  # Higher access tier wins
    FIRST_WRITE_WINS = "first_write"  # First to write wins
    LAST_WRITE_WINS = "last_write"  # Last to write wins


@dataclass
class SessionInfo:
    """Information about an active session."""

    agent_id: str
    session_type: SessionType
    access_tier: AccessTier
    capabilities: list[str]
    started_at: datetime
    last_heartbeat: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "agent_id": self.agent_id,
            "session_type": self.session_type.value,
            "access_tier": self.access_tier.value,
            "capabilities": self.capabilities,
            "started_at": self.started_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SessionInfo:
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            session_type=SessionType(data["session_type"]),
            access_tier=AccessTier(data["access_tier"]),
            capabilities=data.get("capabilities", []),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_stale(self) -> bool:
        """Check if session is stale (no recent heartbeat)."""
        threshold = datetime.now() - timedelta(seconds=STALE_THRESHOLD_SECONDS)
        return self.last_heartbeat < threshold


@dataclass
class ConflictResult:
    """Result of a conflict resolution."""

    winner_agent_id: str
    loser_agent_id: str
    resource_key: str
    strategy_used: ConflictStrategy
    reason: str


def generate_agent_id(session_type: SessionType) -> str:
    """Generate a unique agent ID.

    Format: {session_type}_{timestamp}_{random_suffix}
    Example: claude_20260120_a1b2c3

    Args:
        session_type: Type of session to generate an ID for.

    Returns:
        A unique agent ID string.

    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)  # 6 character hex string
    return f"{session_type.value}_{timestamp}_{suffix}"
