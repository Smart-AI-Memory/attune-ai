"""CrossSessionCoordinator for multi-session agent communication.

Manages session discovery, heartbeat, conflict resolution, distributed
locking, event handling, and cleanup for agents across Claude Code
sessions.

Requires Redis (not available in mock mode).

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog

from attune.memory.features import MemoryFeatures
from attune.memory.short_term import (
    AccessTier,
    AgentCredentials,
    RedisShortTermMemory,
)
from attune.memory.types import parse_stored_record

from .conflicts import (
    resolve_by_priority,
    resolve_first_write,
    resolve_last_write,
)
from .models import (
    CHANNEL_SESSIONS,
    HEARTBEAT_INTERVAL_SECONDS,
    KEY_ACTIVE_AGENTS,
    ConflictResult,
    ConflictStrategy,
    SessionInfo,
    SessionType,
    generate_agent_id,
)

logger = structlog.get_logger(__name__)


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
            memory: RedisShortTermMemory instance (mock mode allowed —
                coordination runs in degraded mode without Redis)
            session_type: Type of this session
            access_tier: Access tier for this session
            capabilities: List of capabilities this session supports
            auto_announce: Whether to announce presence on init

        Note:
            When memory is in mock mode or Redis is unavailable, the
            coordinator initializes in degraded mode (logs a warning;
            cross-process coordination features are unavailable) rather
            than raising.

        """
        # Verify Redis is available -- degrade gracefully in mock mode
        self._degraded = False
        if memory.use_mock or not MemoryFeatures.check_redis():
            import logging

            logging.getLogger(__name__).warning(
                "Cross-session coordination running in degraded mode "
                "(no Redis). Cross-process agent coordination and "
                "distributed features are unavailable.",
            )
            self._degraded = True

        self._memory = memory
        self._session_type = session_type
        self._access_tier = access_tier
        self._capabilities = capabilities or [
            "stash",
            "retrieve",
            "queue",
            "signal",
        ]

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

        session_data = json.dumps(self._session_info.to_dict())
        client.hset(KEY_ACTIVE_AGENTS, self._agent_id, session_data)

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

        client.hdel(KEY_ACTIVE_AGENTS, self._agent_id)

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

        sessions: list[SessionInfo] = []
        all_agents = client.hgetall(KEY_ACTIVE_AGENTS)

        for agent_id, session_data in all_agents.items():
            try:
                if isinstance(agent_id, bytes):
                    agent_id = agent_id.decode()
                if isinstance(session_data, bytes):
                    session_data = session_data.decode()

                info = parse_stored_record(SessionInfo, session_data, key=str(agent_id))
                if info is None:
                    continue

                if info.is_stale:
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
            info = parse_stored_record(SessionInfo, session_data, key=agent_id)
            return info if info is not None and not info.is_stale else None
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
            return resolve_by_priority(
                self._agent_id,
                self._access_tier,
                self._session_info,
                resource_key,
                other_session,
            )
        if strategy == ConflictStrategy.FIRST_WRITE_WINS:
            return resolve_first_write(
                self._agent_id,
                self._memory._client,
                resource_key,
                other_session,
            )
        # LAST_WRITE_WINS
        return resolve_last_write(
            self._agent_id,
            resource_key,
            other_session,
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
        # SET nx+ex is ONE command. SETNX followed by EXPIRE is two, and a
        # crash in the window leaves an immortal lock with no reaper —
        # acquire_lock() then returns False forever (library-review H2).
        acquired = client.set(lock_key, self._agent_id, nx=True, ex=timeout_seconds)

        if acquired:
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

    def on_session_joined(
        self,
        handler: Callable[[SessionInfo], None],
    ) -> None:
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
                data: Any = message["data"]
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
