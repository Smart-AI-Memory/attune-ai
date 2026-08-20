"""Background service and convenience functions for cross-session coordination.

Provides:
- BackgroundService: persistent daemon for session registry maintenance,
  stale-session cleanup, and conflict mediation.
- check_redis_cross_session_support: quick availability check.
- get_or_start_service: helper to obtain a running service instance.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Any

import structlog

from attune.memory.short_term import AccessTier, RedisShortTermMemory

from .coordinator import CrossSessionCoordinator
from .models import (
    KEY_SERVICE_HEARTBEAT,
    KEY_SERVICE_LOCK,
    SERVICE_LOCK_TTL_SECONDS,
    SessionType,
)

logger = structlog.get_logger(__name__)


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
            auto_start_on_connect: Start automatically when first
                session connects

        """
        if memory.use_mock:
            raise ValueError(
                "Background service requires Redis. "
                "Mock mode does not support cross-session features.",
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
            True if started, False if already running or
            couldn't acquire lock

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
            capabilities=[
                "coordinate",
                "aggregate",
                "cleanup",
                "promote",
            ],
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

        # SET nx+ex — genuinely atomic. SETNX then EXPIRE is two commands,
        # and a crash in the window left this singleton lock immortal, so
        # the background service could never start again (library-review H2:
        # the comment here used to claim SETNX was the atomic form).
        acquired = client.set(KEY_SERVICE_LOCK, os.getpid(), nx=True, ex=SERVICE_LOCK_TTL_SECONDS)
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
            client.set(
                KEY_SERVICE_HEARTBEAT,
                datetime.now().isoformat(),
            )

    def _service_loop(self) -> None:
        """Main service loop."""
        cleanup_interval = 60  # Clean up stale sessions every 60s
        last_cleanup = time.time()

        while not self._stop_event.wait(10):  # Check every 10s
            try:
                # Refresh service lock
                self._refresh_service_lock()

                # Periodic cleanup
                if time.time() - last_cleanup > cleanup_interval:
                    self._cleanup_stale_sessions()
                    last_cleanup = time.time()

            except Exception as e:  # noqa: BLE001
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
            "agent_id": (self._coordinator.agent_id if self._coordinator else None),
            "active_sessions": 0,
        }

        if self._coordinator:
            sessions = self._coordinator.get_active_sessions()
            status["active_sessions"] = len(sessions)
            status["sessions"] = [s.to_dict() for s in sessions]

        return status


# === Convenience Functions ===


def check_redis_cross_session_support(
    memory: RedisShortTermMemory,
) -> bool:
    """Check if Redis supports cross-session communication.

    Args:
        memory: RedisShortTermMemory instance

    Returns:
        True if Redis is available and not in mock mode

    """
    return not memory.use_mock and memory._client is not None


def get_or_start_service(
    memory: RedisShortTermMemory,
) -> BackgroundService | None:
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
