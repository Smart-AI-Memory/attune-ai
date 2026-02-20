"""Cross-Session Agent Communication Protocol.

This package enables agents across different Claude Code sessions to
communicate and coordinate via Redis-backed short-term memory.

Features:
- Session discovery and announcement
- Priority-based conflict resolution
- Task queue coordination
- Shared state management
- Agent-to-agent signaling

Requires Redis (not available in mock mode).

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from .coordinator import CrossSessionCoordinator
from .models import (
    CHANNEL_SESSIONS,
    HEARTBEAT_INTERVAL_SECONDS,
    KEY_ACTIVE_AGENTS,
    KEY_SERVICE_HEARTBEAT,
    KEY_SERVICE_LOCK,
    SERVICE_LOCK_TTL_SECONDS,
    STALE_THRESHOLD_SECONDS,
    ConflictResult,
    ConflictStrategy,
    SessionInfo,
    SessionType,
    generate_agent_id,
)
from .service import (
    BackgroundService,
    check_redis_cross_session_support,
    get_or_start_service,
)

__all__ = [
    "BackgroundService",
    "CHANNEL_SESSIONS",
    "ConflictResult",
    "ConflictStrategy",
    "CrossSessionCoordinator",
    "HEARTBEAT_INTERVAL_SECONDS",
    "KEY_ACTIVE_AGENTS",
    "KEY_SERVICE_HEARTBEAT",
    "KEY_SERVICE_LOCK",
    "SERVICE_LOCK_TTL_SECONDS",
    "STALE_THRESHOLD_SECONDS",
    "SessionInfo",
    "SessionType",
    "check_redis_cross_session_support",
    "generate_agent_id",
    "get_or_start_service",
]
