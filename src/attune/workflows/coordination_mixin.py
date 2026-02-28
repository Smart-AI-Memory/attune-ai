"""Coordination Mixin for BaseWorkflow.

Extracted from BaseWorkflow to improve maintainability.
Provides agent coordination, adaptive routing, heartbeat tracking, and signal handling.

Expected attributes on the host class:
    name (str): Workflow name
    _enable_adaptive_routing (bool): Whether adaptive routing is enabled
    _adaptive_router: AdaptiveModelRouter instance (lazy)
    _enable_heartbeat_tracking (bool): Whether heartbeat tracking is enabled
    _heartbeat_coordinator: HeartbeatCoordinator instance (lazy)
    _enable_coordination (bool): Whether coordination signals are enabled
    _coordination_signals: CoordinationSignals instance (lazy)
    _agent_id (str | None): Agent identifier

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .compat import ModelTier

logger = logging.getLogger(__name__)

# Import telemetry availability flag
try:
    from attune.telemetry import UsageTracker

    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    UsageTracker = None  # type: ignore


class CoordinationMixin:
    """Mixin providing agent coordination, adaptive routing, and heartbeat tracking."""

    # Expected attributes (set by BaseWorkflow.__init__)
    name: str
    _enable_adaptive_routing: bool
    _adaptive_router: Any
    _enable_heartbeat_tracking: bool
    _heartbeat_coordinator: Any
    _enable_coordination: bool
    _coordination_signals: Any
    _agent_id: str | None

    def _get_adaptive_router(self):
        """Get or create AdaptiveModelRouter instance (lazy initialization).

        Returns:
            AdaptiveModelRouter instance if telemetry is available, None otherwise

        """
        if not self._enable_adaptive_routing:
            return None

        if self._adaptive_router is None:
            # Lazy import to avoid circular dependencies
            try:
                from attune.models import AdaptiveModelRouter

                if TELEMETRY_AVAILABLE and UsageTracker is not None:
                    self._adaptive_router = AdaptiveModelRouter(
                        telemetry=UsageTracker.get_instance(),
                    )
                    logger.debug(
                        "adaptive_routing_initialized",
                        workflow=self.name,
                        message="Adaptive routing enabled for cost optimization",
                    )
                else:
                    logger.warning(
                        "adaptive_routing_unavailable",
                        workflow=self.name,
                        message="Telemetry not available, adaptive routing disabled",
                    )
                    self._enable_adaptive_routing = False
            except ImportError as e:
                logger.warning(
                    "adaptive_routing_import_error",
                    workflow=self.name,
                    error=str(e),
                    message="Failed to import AdaptiveModelRouter",
                )
                self._enable_adaptive_routing = False

        return self._adaptive_router

    def _get_heartbeat_coordinator(self):
        """Get or create HeartbeatCoordinator instance (lazy initialization).

        Returns:
            HeartbeatCoordinator instance if heartbeat tracking is enabled, None otherwise

        """
        if not self._enable_heartbeat_tracking:
            return None

        if self._heartbeat_coordinator is None:
            try:
                from attune.telemetry import HeartbeatCoordinator

                self._heartbeat_coordinator = HeartbeatCoordinator()
                logger.debug(
                    "heartbeat_tracking_initialized",
                    workflow=self.name,
                    agent_id=self._agent_id,
                    message="Heartbeat tracking enabled for agent liveness monitoring",
                )
            except ImportError as e:
                logger.warning(
                    "heartbeat_tracking_import_error",
                    workflow=self.name,
                    error=str(e),
                    message="Failed to import HeartbeatCoordinator",
                )
                self._enable_heartbeat_tracking = False
            except Exception as e:
                logger.warning(
                    "heartbeat_tracking_init_error",
                    workflow=self.name,
                    error=str(e),
                    message="Failed to initialize HeartbeatCoordinator (Redis unavailable?)",
                )
                self._enable_heartbeat_tracking = False

        return self._heartbeat_coordinator

    def _get_coordination_signals(self):
        """Get or create CoordinationSignals instance (lazy initialization).

        Returns:
            CoordinationSignals instance if coordination is enabled, None otherwise

        """
        if not self._enable_coordination:
            return None

        if self._coordination_signals is None:
            try:
                from attune.telemetry import CoordinationSignals

                self._coordination_signals = CoordinationSignals(agent_id=self._agent_id)
                logger.debug(
                    "coordination_initialized",
                    workflow=self.name,
                    agent_id=self._agent_id,
                    message="Coordination signals enabled for inter-agent communication",
                )
            except ImportError as e:
                logger.warning(
                    "coordination_import_error",
                    workflow=self.name,
                    error=str(e),
                    message="Failed to import CoordinationSignals",
                )
                self._enable_coordination = False
            except Exception as e:
                logger.warning(
                    "coordination_init_error",
                    workflow=self.name,
                    error=str(e),
                    message="Failed to initialize CoordinationSignals (Redis unavailable?)",
                )
                self._enable_coordination = False

        return self._coordination_signals

    def _check_adaptive_tier_upgrade(self, stage_name: str, current_tier: ModelTier) -> ModelTier:
        """Check if adaptive routing recommends a tier upgrade.

        Uses historical telemetry to detect if the current tier has a high
        failure rate (>20%) and automatically upgrades to the next tier.

        Args:
            stage_name: Name of the stage
            current_tier: Currently selected tier

        Returns:
            Upgraded tier if recommended, otherwise current_tier

        """
        from .compat import ModelTier

        router = self._get_adaptive_router()
        if router is None:
            return current_tier

        # Check if tier upgrade is recommended
        should_upgrade, reason = router.recommend_tier_upgrade(workflow=self.name, stage=stage_name)

        if should_upgrade:
            # Upgrade to next tier: CHEAP → CAPABLE → PREMIUM
            if current_tier == ModelTier.CHEAP:
                new_tier = ModelTier.CAPABLE
            elif current_tier == ModelTier.CAPABLE:
                new_tier = ModelTier.PREMIUM
            else:
                new_tier = current_tier  # Already at highest tier

            logger.warning(
                "adaptive_routing_tier_upgrade",
                workflow=self.name,
                stage=stage_name,
                old_tier=current_tier.value,
                new_tier=new_tier.value,
                reason=reason,
            )

            return new_tier

        return current_tier

    def send_signal(
        self,
        signal_type: str,
        target_agent: str | None = None,
        payload: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> str:
        """Send a coordination signal to another agent (Pattern 2).

        Args:
            signal_type: Type of signal (e.g., "task_complete", "checkpoint", "error")
            target_agent: Target agent ID (None for broadcast to all agents)
            payload: Optional signal payload data
            ttl_seconds: Optional TTL override (default 60 seconds)

        Returns:
            Signal ID if coordination is enabled, empty string otherwise

        Example:
            >>> # Signal completion to orchestrator
            >>> workflow.send_signal(
            ...     signal_type="task_complete",
            ...     target_agent="orchestrator",
            ...     payload={"result": "success", "data": {...}}
            ... )

            >>> # Broadcast abort to all agents
            >>> workflow.send_signal(
            ...     signal_type="abort",
            ...     target_agent=None,  # Broadcast
            ...     payload={"reason": "user_cancelled"}
            ... )

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
            logger.warning(f"Failed to send coordination signal: {e}")
            return ""

    def wait_for_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> Any:
        """Wait for a coordination signal from another agent (Pattern 2).

        Blocking call that polls for signals with timeout.

        Args:
            signal_type: Type of signal to wait for
            source_agent: Optional source agent filter
            timeout: Maximum wait time in seconds (default 30.0)
            poll_interval: Poll interval in seconds (default 0.5)

        Returns:
            CoordinationSignal if received, None if timeout or coordination disabled

        Example:
            >>> # Wait for orchestrator approval
            >>> signal = workflow.wait_for_signal(
            ...     signal_type="approval",
            ...     source_agent="orchestrator",
            ...     timeout=60.0
            ... )
            >>> if signal:
            ...     proceed_with_deployment(signal.payload)

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
            logger.warning(f"Failed to wait for coordination signal: {e}")
            return None

    def check_signal(
        self,
        signal_type: str,
        source_agent: str | None = None,
        consume: bool = True,
    ) -> Any:
        """Check for a coordination signal without blocking (Pattern 2).

        Non-blocking check for pending signals.

        Args:
            signal_type: Type of signal to check for
            source_agent: Optional source agent filter
            consume: If True, remove signal after reading (default True)

        Returns:
            CoordinationSignal if available, None otherwise

        Example:
            >>> # Non-blocking check for abort signal
            >>> signal = workflow.check_signal(signal_type="abort")
            >>> if signal:
            ...     raise WorkflowAbortedException(signal.payload["reason"])

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
            logger.warning(f"Failed to check coordination signal: {e}")
            return None
