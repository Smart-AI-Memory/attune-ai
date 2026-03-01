"""Cross-session coordination for distributed agents.

This module enables coordination across multiple sessions:
- Enable cross-session communication
- Check cross-session availability
- Coordinate distributed agent activities

Use Cases:
- Multi-process agent coordination
- Distributed workflow execution
- Shared state across sessions

Classes:
    CrossSessionManager: Cross-session coordination operations

Example:
    >>> from attune.memory.short_term.cross_session import CrossSessionManager
    >>> from attune.memory.types import AccessTier
    >>> cross_session = CrossSessionManager(base_ops)
    >>> if cross_session.available():
    ...     coordinator = cross_session.enable(AccessTier.CONTRIBUTOR)
    ...     print(f"Session ID: {coordinator.agent_id}")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.types import AccessTier

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class CrossSessionManager:
    """Cross-session coordination operations.

    Provides coordination capabilities for agents running in
    different Claude Code sessions using Redis as the coordination
    backbone.

    The class is designed to be composed with BaseOperations
    for dependency injection.

    Example:
        >>> cross_session = CrossSessionManager(base_ops)
        >>> if cross_session.available():
        ...     coordinator = cross_session.enable(AccessTier.CONTRIBUTOR)
        ...     sessions = coordinator.get_active_sessions()

    """

    def __init__(self, base: BaseOperations) -> None:
        """Initialize cross-session manager.

        Args:
            base: BaseOperations instance for Redis client access

        """
        self._base = base

    def enable(
        self,
        access_tier: AccessTier = AccessTier.CONTRIBUTOR,
        auto_announce: bool = True,
    ) -> Any:
        """Enable cross-session communication for this memory instance.

        This allows agents in different Claude Code sessions to communicate
        and coordinate via Redis.

        Args:
            access_tier: Access tier for this session
            auto_announce: Whether to announce presence automatically

        Returns:
            CrossSessionCoordinator instance

        Raises:
            ValueError: If in mock mode (Redis required for cross-session)

        Example:
            >>> coordinator = cross_session.enable(AccessTier.CONTRIBUTOR)
            >>> print(f"Session ID: {coordinator.agent_id}")
            >>> sessions = coordinator.get_active_sessions()

        """
        if self._base.use_mock:
            raise ValueError(
                "Cross-session communication requires Redis. "
                "Set REDIS_HOST/REDIS_PORT or disable mock mode.",
            )

        # Import lazily to avoid circular imports
        from attune.memory.cross_session import CrossSessionCoordinator, SessionType

        # The coordinator expects a memory instance with full API
        # For now, pass the base which should be extended by facade
        coordinator = CrossSessionCoordinator(
            memory=self._base,  # type: ignore[arg-type]
            session_type=SessionType.CLAUDE,
            access_tier=access_tier,
            auto_announce=auto_announce,
        )

        return coordinator

    def available(self) -> bool:
        """Check if cross-session communication is available.

        Returns:
            True if Redis is connected (not mock mode)

        Example:
            >>> if cross_session.available():
            ...     coordinator = cross_session.enable()

        """
        return not self._base.use_mock and self._base._client is not None
