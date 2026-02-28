"""Coordination service for workflows.

Standalone service extracted from CoordinationMixin. Provides agent coordination,
adaptive routing, heartbeat tracking, and inter-agent signaling.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class CoordinationService:
    """Service for inter-agent coordination.

    Manages heartbeat tracking, adaptive routing, and coordination signals
    for multi-agent workflows.

    Args:
        workflow_name: Name of the workflow
        agent_id: Agent identifier for signal routing
        enable_heartbeat: Whether to enable heartbeat tracking
        enable_coordination: Whether to enable coordination signals

    Example:
        >>> coord = CoordinationService("code-review", agent_id="agent-1")
        >>> coord.send_signal("task_complete", target_agent="orchestrator")

    """

    def __init__(
        self,
        workflow_name: str,
        agent_id: str | None = None,
        enable_heartbeat: bool = False,
        enable_coordination: bool = False,
    ) -> None:
        self._workflow_name = workflow_name
        self._agent_id = agent_id
        self._enable_heartbeat = enable_heartbeat
        self._enable_coordination = enable_coordination
        self._heartbeat_coordinator: Any = None
        self._coordination_signals: Any = None

    def get_heartbeat_coordinator(self) -> Any:
        """Get or create HeartbeatCoordinator (lazy init).

        Returns:
            HeartbeatCoordinator if available, None otherwise

        """
        if not self._enable_heartbeat:
            return None

        if self._heartbeat_coordinator is None:
            try:
                from attune.telemetry import HeartbeatCoordinator

                self._heartbeat_coordinator = HeartbeatCoordinator()
                logger.debug(f"Heartbeat tracking initialized for {self._workflow_name}")
            except ImportError as e:
                logger.warning(f"HeartbeatCoordinator import failed: {e}")
                self._enable_heartbeat = False
            except Exception as e:
                # INTENTIONAL: Redis unavailable shouldn't crash workflow
                logger.warning(f"HeartbeatCoordinator init failed: {e}")
                self._enable_heartbeat = False

        return self._heartbeat_coordinator

    def send_signal(
        self,
        signal_type: str,
        target_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Send a coordination signal to another agent.

        Args:
            signal_type: Type of signal (e.g., "task_complete", "error")
            target_agent: Target agent ID (None for broadcast)
            payload: Optional signal payload data
            ttl_seconds: Optional TTL override (default 60 seconds)

        Returns:
            Signal ID if sent, empty string otherwise

        """
        coordinator = self._get_coordination_signals()
        if coordinator is None:
            return ""

        try:
            return coordinator.signal(
                signal_type=signal_type,
                source_agent=self._agent_id,
                target_agent=target_agent,
                payload=payload or {},
                ttl_seconds=ttl_seconds,
            )
        except Exception as e:
            # INTENTIONAL: Signal failure shouldn't crash workflow
            logger.warning(f"Failed to send coordination signal: {e}")
            return ""

    def wait_for_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> Any:
        """Wait for a coordination signal (blocking).

        Args:
            signal_type: Type of signal to wait for
            source_agent: Optional source agent filter
            timeout: Maximum wait time in seconds
            poll_interval: Poll interval in seconds

        Returns:
            CoordinationSignal if received, None if timeout

        """
        coordinator = self._get_coordination_signals()
        if coordinator is None:
            return None

        try:
            return coordinator.wait_for_signal(
                signal_type=signal_type,
                source_agent=source_agent,
                timeout=timeout,
                poll_interval=poll_interval,
            )
        except Exception as e:
            # INTENTIONAL: Signal failure shouldn't crash workflow
            logger.warning(f"Failed to wait for signal: {e}")
            return None

    def check_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        consume: bool = True,
    ) -> Any:
        """Check for a coordination signal (non-blocking).

        Args:
            signal_type: Type of signal to check for
            source_agent: Optional source agent filter
            consume: If True, remove signal after reading

        Returns:
            CoordinationSignal if available, None otherwise

        """
        coordinator = self._get_coordination_signals()
        if coordinator is None:
            return None

        try:
            return coordinator.check_signal(
                signal_type=signal_type,
                source_agent=source_agent,
                consume=consume,
            )
        except Exception as e:
            # INTENTIONAL: Signal failure shouldn't crash workflow
            logger.warning(f"Failed to check signal: {e}")
            return None

    def _get_coordination_signals(self) -> Any:
        """Get or create CoordinationSignals (lazy init)."""
        if not self._enable_coordination:
            return None

        if self._coordination_signals is None:
            try:
                from attune.telemetry import CoordinationSignals

                self._coordination_signals = CoordinationSignals(agent_id=self._agent_id)
                logger.debug(f"Coordination signals initialized for {self._workflow_name}")
            except ImportError as e:
                logger.warning(f"CoordinationSignals import failed: {e}")
                self._enable_coordination = False
            except Exception as e:
                # INTENTIONAL: Redis unavailable shouldn't crash workflow
                logger.warning(f"CoordinationSignals init failed: {e}")
                self._enable_coordination = False

        return self._coordination_signals
