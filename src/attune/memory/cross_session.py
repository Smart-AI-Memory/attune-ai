"""Cross-Session Agent Communication Protocol.

This module enables agents across different Claude Code sessions to communicate
and coordinate via Redis-backed short-term memory.

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

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog

from attune.memory.features import MemoryFeatures

from .short_term import AccessTier, AgentCredentials, RedisShortTermMemory

logger = structlog.get_logger(__name__)


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
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = secrets.token_hex(3)  # 6 character hex string
    return f"{session_type.value}_{timestamp}_{suffix}"


class CrossSessionCoordinator:
    """Coordinator for cross-session agent communication.

    This class manages session discovery, conflict resolution, and
    coordination between agents across different Claude Code sessions.

    Requires Redis - not available in mock mode.
    """

    def __init__(
        self,
        memory: RedisShortTermMemory,
        session_type: SessionType = SessionType.CLAUDE,
        access_tier: AccessTier = AccessTier.CONTRIBUTOR,
        capabilities: list[str] | None = None,
        auto_announce: bool = True,
    ):
        """Initialize cross-session coordinator.

        Args:
            memory: RedisShortTermMemory instance (must not be mock)
            session_type: Type of this session
            access_tier: Access tier for this session
            capabilities: List of capabilities this session supports
            auto_announce: Whether to announce presence on init

        Raises:
            ValueError: If memory is in mock mode (Redis required)
            ImportError: If Redis package is not installed
        """
        # Verify Redis is available — degrade gracefully in mock mode
        self._degraded = False
        if memory.use_mock or not MemoryFeatures.check_redis():
            import logging

            logging.getLogger(__name__).warning(
                "Cross-session coordination running in degraded mode (no Redis). "
                "Cross-process agent coordination and distributed features are unavailable."
            )
            self._degraded = True

        self._memory = memory
        self._session_type = session_type
        self._access_tier = access_tier
        self._capabilities = capabilities or ["stash", "retrieve", "queue", "signal"]

        # Generate unique agent ID
        self._agent_id = generate_agent_id(session_type)
        self._credentials = AgentCredentials(
            agent_id=self._agent_id,
            tier=access_tier,
        )

        # Session info
        self._session_info = SessionInfo(
            agent_id=self._agent_id,
            session_type=session_type,
            access_tier=access_tier,
            capabilities=self._capabilities,
            started_at=datetime.now(),
            last_heartbeat=datetime.now(),
        )

        # Heartbeat thread
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_stop = threading.Event()

        # Event handlers
        self._on_session_joined: list[Callable[[SessionInfo], None]] = []
        self._on_session_left: list[Callable[[str], None]] = []

        # Auto-announce if requested
        if auto_announce:
            self.announce()
            self.start_heartbeat()

        logger.info(
            "cross_session_coordinator_initialized",
            agent_id=self._agent_id,
            session_type=session_type.value,
            access_tier=access_tier.name,
        )

    @property
    def agent_id(self) -> str:
        """Get this session's agent ID."""
        return self._agent_id

    @property
    def credentials(self) -> AgentCredentials:
        """Get this session's credentials."""
        return self._credentials

    @property
    def session_info(self) -> SessionInfo:
        """Get this session's info."""
        return self._session_info

    # === Session Discovery ===

    def announce(self) -> None:
        """Announce this session's presence to other sessions."""
        client = self._memory._client
        if client is None:
            return

        # Update active agents registry
        session_data = json.dumps(self._session_info.to_dict())
        client.hset(KEY_ACTIVE_AGENTS, self._agent_id, session_data)

        # Publish announcement to sessions channel
        announcement = {
            "event": "session_joined",
            "session": self._session_info.to_dict(),
        }
        client.publish(CHANNEL_SESSIONS, json.dumps(announcement))

        logger.info(
            "session_announced",
            agent_id=self._agent_id,
            session_type=self._session_type.value,
        )

    def depart(self) -> None:
        """Announce this session's departure."""
        self.stop_heartbeat()

        client = self._memory._client
        if client is None:
            return

        # Remove from active agents registry
        client.hdel(KEY_ACTIVE_AGENTS, self._agent_id)

        # Publish departure to sessions channel
        departure = {
            "event": "session_left",
            "agent_id": self._agent_id,
        }
        client.publish(CHANNEL_SESSIONS, json.dumps(departure))

        logger.info("session_departed", agent_id=self._agent_id)

    def get_active_sessions(self) -> list[SessionInfo]:
        """Get all active sessions.

        Returns:
            List of SessionInfo for all active sessions
        """
        client = self._memory._client
        if client is None:
            return []

        sessions = []
        all_agents = client.hgetall(KEY_ACTIVE_AGENTS)

        for agent_id, session_data in all_agents.items():
            try:
                # Decode bytes if necessary
                if isinstance(agent_id, bytes):
                    agent_id = agent_id.decode()
                if isinstance(session_data, bytes):
                    session_data = session_data.decode()

                info = SessionInfo.from_dict(json.loads(session_data))

                # Skip stale sessions
                if info.is_stale:
                    # Clean up stale session
                    client.hdel(KEY_ACTIVE_AGENTS, agent_id)
                    logger.debug("cleaned_stale_session", agent_id=agent_id)
                    continue

                sessions.append(info)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(
                    "invalid_session_data",
                    agent_id=agent_id,
                    error=str(e),
                )

        return sessions

    def get_session(self, agent_id: str) -> SessionInfo | None:
        """Get info for a specific session.

        Args:
            agent_id: Agent ID to look up

        Returns:
            SessionInfo if found and not stale, None otherwise
        """
        client = self._memory._client
        if client is None:
            return None

        session_data = client.hget(KEY_ACTIVE_AGENTS, agent_id)
        if session_data is None:
            return None

        try:
            if isinstance(session_data, bytes):
                session_data = session_data.decode()
            info = SessionInfo.from_dict(json.loads(session_data))
            return info if not info.is_stale else None
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    # === Heartbeat ===

    def start_heartbeat(self) -> None:
        """Start the heartbeat thread."""
        if self._heartbeat_thread is not None:
            return

        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat-{self._agent_id}",
        )
        self._heartbeat_thread.start()
        logger.debug("heartbeat_started", agent_id=self._agent_id)

    def stop_heartbeat(self) -> None:
        """Stop the heartbeat thread."""
        if self._heartbeat_thread is None:
            return

        self._heartbeat_stop.set()
        self._heartbeat_thread.join(timeout=5)
        self._heartbeat_thread = None
        logger.debug("heartbeat_stopped", agent_id=self._agent_id)

    def _heartbeat_loop(self) -> None:
        """Heartbeat loop - runs in background thread."""
        while not self._heartbeat_stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            self._send_heartbeat()

    def _send_heartbeat(self) -> None:
        """Send a heartbeat update."""
        client = self._memory._client
        if client is None:
            return

        # Update last heartbeat
        self._session_info.last_heartbeat = datetime.now()
        session_data = json.dumps(self._session_info.to_dict())
        client.hset(KEY_ACTIVE_AGENTS, self._agent_id, session_data)

    # === Conflict Resolution ===

    def resolve_conflict(
        self,
        resource_key: str,
        other_agent_id: str,
        strategy: ConflictStrategy = ConflictStrategy.PRIORITY_BASED,
    ) -> ConflictResult:
        """Resolve a conflict between this session and another.

        Args:
            resource_key: Key of the contested resource
            other_agent_id: Agent ID of the other party
            strategy: Strategy to use for resolution

        Returns:
            ConflictResult with winner and loser
        """
        other_session = self.get_session(other_agent_id)

        if strategy == ConflictStrategy.PRIORITY_BASED:
            return self._resolve_by_priority(resource_key, other_session)
        elif strategy == ConflictStrategy.FIRST_WRITE_WINS:
            return self._resolve_first_write(resource_key, other_session)
        else:  # LAST_WRITE_WINS
            return self._resolve_last_write(resource_key, other_session)

    def _resolve_by_priority(
        self,
        resource_key: str,
        other_session: SessionInfo | None,
    ) -> ConflictResult:
        """Resolve conflict using priority (access tier)."""
        my_tier = self._access_tier.value
        other_tier = other_session.access_tier.value if other_session else 0
        other_id = other_session.agent_id if other_session else "unknown"

        if my_tier > other_tier:
            winner, loser = self._agent_id, other_id
            reason = f"Higher tier ({self._access_tier.name} > {other_session.access_tier.name if other_session else 'N/A'})"
        elif my_tier < other_tier:
            winner, loser = other_id, self._agent_id
            reason = f"Higher tier ({other_session.access_tier.name if other_session else 'N/A'} > {self._access_tier.name})"
        else:
            # Equal tier - use timestamp (first write wins)
            if other_session and other_session.started_at < self._session_info.started_at:
                winner, loser = other_id, self._agent_id
                reason = "Equal tier, earlier session wins"
            else:
                winner, loser = self._agent_id, other_id
                reason = "Equal tier, earlier session wins"

        return ConflictResult(
            winner_agent_id=winner,
            loser_agent_id=loser,
            resource_key=resource_key,
            strategy_used=ConflictStrategy.PRIORITY_BASED,
            reason=reason,
        )

    def _resolve_first_write(
        self,
        resource_key: str,
        other_session: SessionInfo | None,
    ) -> ConflictResult:
        """Resolve conflict using first-write-wins."""
        # Check who owns the resource
        client = self._memory._client
        if client is None:
            return ConflictResult(
                winner_agent_id=self._agent_id,
                loser_agent_id=other_session.agent_id if other_session else "unknown",
                resource_key=resource_key,
                strategy_used=ConflictStrategy.FIRST_WRITE_WINS,
                reason="No Redis connection - local wins",
            )

        # Try to get lock on resource
        lock_key = f"empathy:lock:{resource_key}"
        acquired = client.setnx(lock_key, self._agent_id)

        if acquired:
            client.expire(lock_key, 300)  # 5 minute lock
            winner, loser = self._agent_id, other_session.agent_id if other_session else "unknown"
            reason = "First to acquire lock"
        else:
            current_owner = client.get(lock_key)
            if isinstance(current_owner, bytes):
                current_owner = current_owner.decode()
            winner = current_owner or "unknown"
            loser = self._agent_id
            reason = "Lock already held"

        return ConflictResult(
            winner_agent_id=winner,
            loser_agent_id=loser,
            resource_key=resource_key,
            strategy_used=ConflictStrategy.FIRST_WRITE_WINS,
            reason=reason,
        )

    def _resolve_last_write(
        self,
        resource_key: str,
        other_session: SessionInfo | None,
    ) -> ConflictResult:
        """Resolve conflict using last-write-wins (current writer wins)."""
        return ConflictResult(
            winner_agent_id=self._agent_id,
            loser_agent_id=other_session.agent_id if other_session else "unknown",
            resource_key=resource_key,
            strategy_used=ConflictStrategy.LAST_WRITE_WINS,
            reason="Last write wins - current writer takes precedence",
        )

    # === Distributed Locking ===

    def acquire_lock(
        self,
        resource_key: str,
        timeout_seconds: int = 300,
    ) -> bool:
        """Acquire a distributed lock on a resource.

        Args:
            resource_key: Key of the resource to lock
            timeout_seconds: Lock timeout in seconds

        Returns:
            True if lock acquired, False otherwise
        """
        client = self._memory._client
        if client is None:
            return False

        lock_key = f"empathy:lock:{resource_key}"
        acquired = client.setnx(lock_key, self._agent_id)

        if acquired:
            client.expire(lock_key, timeout_seconds)
            logger.debug(
                "lock_acquired",
                resource_key=resource_key,
                agent_id=self._agent_id,
            )

        return bool(acquired)

    def release_lock(self, resource_key: str) -> bool:
        """Release a distributed lock.

        Args:
            resource_key: Key of the resource to unlock

        Returns:
            True if lock released, False if not owner
        """
        client = self._memory._client
        if client is None:
            return False

        lock_key = f"empathy:lock:{resource_key}"
        current_owner = client.get(lock_key)

        if current_owner:
            if isinstance(current_owner, bytes):
                current_owner = current_owner.decode()
            if current_owner == self._agent_id:
                client.delete(lock_key)
                logger.debug(
                    "lock_released",
                    resource_key=resource_key,
                    agent_id=self._agent_id,
                )
                return True

        return False

    def check_lock(self, resource_key: str) -> str | None:
        """Check who holds a lock on a resource.

        Args:
            resource_key: Key of the resource

        Returns:
            Agent ID of lock holder, or None if unlocked
        """
        client = self._memory._client
        if client is None:
            return None

        lock_key = f"empathy:lock:{resource_key}"
        owner = client.get(lock_key)

        if owner:
            if isinstance(owner, bytes):
                return owner.decode()
            return str(owner)

        return None

    # === Event Handlers ===

    def on_session_joined(self, handler: Callable[[SessionInfo], None]) -> None:
        """Register handler for when a session joins.

        Args:
            handler: Callback receiving SessionInfo of joining session
        """
        self._on_session_joined.append(handler)

    def on_session_left(self, handler: Callable[[str], None]) -> None:
        """Register handler for when a session leaves.

        Args:
            handler: Callback receiving agent_id of departing session
        """
        self._on_session_left.append(handler)

    def subscribe_to_sessions(self) -> None:
        """Subscribe to session events (join/leave).

        Note: This blocks and should be called in a separate thread.
        """
        client = self._memory._client
        if client is None:
            return

        pubsub = client.pubsub()
        pubsub.subscribe(CHANNEL_SESSIONS)

        for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                event = json.loads(data)

                if event.get("event") == "session_joined":
                    session_info = SessionInfo.from_dict(event["session"])
                    for joined_handler in self._on_session_joined:
                        joined_handler(session_info)
                elif event.get("event") == "session_left":
                    agent_id = event["agent_id"]
                    for left_handler in self._on_session_left:
                        left_handler(agent_id)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning("invalid_session_event", error=str(e))

    # === Cleanup ===

    def close(self) -> None:
        """Clean up and depart."""
        self.depart()


# === Background Service ===


class BackgroundService:
    """Background service daemon for cross-session coordination.

    This service runs persistently to:
    - Maintain registry of active sessions
    - Aggregate results from completed tasks
    - Clean up stale session data
    - Coordinate conflict resolution
    - Promote patterns to long-term memory (when ready)
    """

    def __init__(
        self,
        memory: RedisShortTermMemory,
        auto_start_on_connect: bool = True,
    ):
        """Initialize background service.

        Args:
            memory: RedisShortTermMemory instance
            auto_start_on_connect: Start automatically when first session connects
        """
        if memory.use_mock:
            raise ValueError(
                "Background service requires Redis. "
                "Mock mode does not support cross-session features."
            )

        self._memory = memory
        self._auto_start = auto_start_on_connect
        self._coordinator: CrossSessionCoordinator | None = None
        self._running = False
        self._service_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        logger.info("background_service_initialized")

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running

    def start(self) -> bool:
        """Start the background service.

        Returns:
            True if started, False if already running or couldn't acquire lock
        """
        if self._running:
            logger.warning("service_already_running")
            return False

        # Try to acquire service lock (only one service can run)
        if not self._acquire_service_lock():
            logger.warning("service_lock_held_by_another")
            return False

        # Create coordinator for service
        self._coordinator = CrossSessionCoordinator(
            memory=self._memory,
            session_type=SessionType.SERVICE,
            access_tier=AccessTier.STEWARD,
            capabilities=["coordinate", "aggregate", "cleanup", "promote"],
            auto_announce=True,
        )

        # Start service loop
        self._running = True
        self._stop_event.clear()
        self._service_thread = threading.Thread(
            target=self._service_loop,
            daemon=True,
            name="empathy-service",
        )
        self._service_thread.start()

        logger.info(
            "background_service_started",
            agent_id=self._coordinator.agent_id,
        )
        return True

    def stop(self) -> None:
        """Stop the background service."""
        if not self._running:
            return

        self._stop_event.set()

        if self._service_thread:
            self._service_thread.join(timeout=10)
            self._service_thread = None

        if self._coordinator:
            self._coordinator.close()
            self._coordinator = None

        self._release_service_lock()
        self._running = False

        logger.info("background_service_stopped")

    def _acquire_service_lock(self) -> bool:
        """Try to acquire the service lock."""
        client = self._memory._client
        if client is None:
            return False

        # Use SETNX for atomic lock acquisition
        acquired = client.setnx(KEY_SERVICE_LOCK, os.getpid())
        if acquired:
            client.expire(KEY_SERVICE_LOCK, SERVICE_LOCK_TTL_SECONDS)
        return bool(acquired)

    def _release_service_lock(self) -> None:
        """Release the service lock."""
        client = self._memory._client
        if client:
            client.delete(KEY_SERVICE_LOCK)

    def _refresh_service_lock(self) -> None:
        """Refresh the service lock TTL."""
        client = self._memory._client
        if client:
            client.expire(KEY_SERVICE_LOCK, SERVICE_LOCK_TTL_SECONDS)
            client.set(KEY_SERVICE_HEARTBEAT, datetime.now().isoformat())

    def _service_loop(self) -> None:
        """Main service loop."""
        cleanup_interval = 60  # Clean up stale sessions every 60 seconds
        last_cleanup = time.time()

        while not self._stop_event.wait(10):  # Check every 10 seconds
            try:
                # Refresh service lock
                self._refresh_service_lock()

                # Periodic cleanup
                if time.time() - last_cleanup > cleanup_interval:
                    self._cleanup_stale_sessions()
                    last_cleanup = time.time()

            except Exception as e:
                logger.exception("service_loop_error", error=str(e))

    def _cleanup_stale_sessions(self) -> None:
        """Clean up stale session data."""
        if not self._coordinator:
            return

        # Get all sessions (this already cleans stale ones)
        sessions = self._coordinator.get_active_sessions()
        logger.debug(
            "cleanup_completed",
            active_sessions=len(sessions),
        )

    def get_status(self) -> dict[str, Any]:
        """Get service status.

        Returns:
            Dict with service status information
        """
        status: dict[str, Any] = {
            "running": self._running,
            "agent_id": self._coordinator.agent_id if self._coordinator else None,
            "active_sessions": 0,
        }

        if self._coordinator:
            sessions = self._coordinator.get_active_sessions()
            status["active_sessions"] = len(sessions)
            status["sessions"] = [s.to_dict() for s in sessions]

        return status


# === Convenience Functions ===


def check_redis_cross_session_support(memory: RedisShortTermMemory) -> bool:
    """Check if Redis supports cross-session communication.

    Args:
        memory: RedisShortTermMemory instance

    Returns:
        True if Redis is available and not in mock mode
    """
    return not memory.use_mock and memory._client is not None


def get_or_start_service(memory: RedisShortTermMemory) -> BackgroundService | None:
    """Get existing service or start a new one.

    Args:
        memory: RedisShortTermMemory instance

    Returns:
        BackgroundService if started/running, None if unavailable
    """
    if not check_redis_cross_session_support(memory):
        return None

    service = BackgroundService(memory)
    if service.start():
        return service

    # Service already running elsewhere
    return None
