"""Short-Term Memory Mixin for EmpathyOS.

Extracted from EmpathyOS to improve maintainability.
Provides Redis-backed short-term memory methods for multi-agent coordination,
pattern staging, signal sending/receiving, and collaboration state persistence.

Expected attributes on the host class:
    user_id (str): User identifier
    short_term_memory (MemoryBackend | None): Redis memory instance
    credentials (AgentCredentials): Agent credentials
    collaboration_state (CollaborationState): Collaboration state
    current_empathy_level (int): Current empathy level
    logger (logging.Logger): Logger instance
    _session_id (str | None): Session ID (lazily generated)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..memory.backend import MemoryBackend
    from ..memory.types import AgentCredentials, StagedPattern


class ShortTermMemoryMixin:
    """Mixin providing Redis-backed short-term memory coordination."""

    # Expected attributes (set by EmpathyOS.__init__)
    user_id: str
    short_term_memory: MemoryBackend | None
    credentials: AgentCredentials
    collaboration_state: Any  # CollaborationState
    current_empathy_level: int
    logger: Any  # logging.Logger
    _session_id: str | None

    def has_short_term_memory(self) -> bool:
        """Check if this agent has short-term memory configured."""
        return self.short_term_memory is not None

    @property
    def session_id(self) -> str:
        """Get or generate a unique session ID for this agent instance."""
        if self._session_id is None:
            import uuid

            self._session_id = f"{self.user_id}_{uuid.uuid4().hex[:8]}"
        return self._session_id

    def stage_pattern(self, pattern: StagedPattern) -> bool:
        """Stage a discovered pattern for validation.

        Patterns are held in a staging area until a Validator promotes them
        to the active pattern library. This implements the trust-but-verify
        approach to multi-agent knowledge building.

        Args:
            pattern: StagedPattern with discovery details

        Returns:
            True if staged successfully

        Raises:
            RuntimeError: If no short-term memory configured
            PermissionError: If agent lacks Contributor+ access

        Example:
            >>> from attune import StagedPattern
            >>> pattern = StagedPattern(
            ...     pattern_id="pat_auth_001",
            ...     agent_id=empathy.user_id,
            ...     pattern_type="security",
            ...     name="JWT Token Refresh Pattern",
            ...     description="Refresh tokens before expiry to prevent auth failures",
            ...     confidence=0.85,
            ... )
            >>> empathy.stage_pattern(pattern)

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable pattern staging.",
            )
        return self.short_term_memory.stage_pattern(pattern, self.credentials)

    def get_staged_patterns(self) -> list[StagedPattern]:
        """Get all patterns currently in staging.

        Returns patterns staged by any agent that are awaiting validation.
        Validators use this to review and promote/reject patterns.

        Returns:
            List of StagedPattern objects

        Raises:
            RuntimeError: If no short-term memory configured

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable pattern staging.",
            )
        return self.short_term_memory.list_staged_patterns(self.credentials)

    def send_signal(
        self,
        signal_type: str,
        data: dict,
        target_agent: str | None = None,
    ) -> bool:
        """Send a coordination signal to other agents.

        Use signals for real-time coordination:
        - Notify completion of tasks
        - Request assistance
        - Broadcast status updates

        Args:
            signal_type: Type of signal (e.g., "task_complete", "need_review")
            data: Signal payload
            target_agent: Specific agent to target, or None for broadcast

        Returns:
            True if sent successfully

        Raises:
            RuntimeError: If no short-term memory configured

        Example:
            >>> # Notify specific agent
            >>> empathy.send_signal(
            ...     "analysis_complete",
            ...     {"files": 10, "issues_found": 3},
            ...     target_agent="lead_reviewer"
            ... )
            >>> # Broadcast to all
            >>> empathy.send_signal("status_update", {"phase": "testing"})

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable coordination signals.",
            )
        return self.short_term_memory.send_signal(
            signal_type=signal_type,
            data=data,
            credentials=self.credentials,
            target_agent=target_agent,
        )

    def receive_signals(self, signal_type: str | None = None) -> list[dict]:
        """Receive coordination signals from other agents.

        Returns signals targeted at this agent or broadcast signals.
        Signals expire after 5 minutes (TTL).

        Args:
            signal_type: Filter by signal type, or None for all

        Returns:
            List of signal dicts with sender, type, data, timestamp

        Raises:
            RuntimeError: If no short-term memory configured

        Example:
            >>> signals = empathy.receive_signals("analysis_complete")
            >>> for sig in signals:
            ...     print(f"From {sig['sender']}: {sig['data']}")

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable coordination signals.",
            )
        return self.short_term_memory.receive_signals(self.credentials, signal_type=signal_type)

    def persist_collaboration_state(self) -> bool:
        """Persist current collaboration state to short-term memory.

        Call periodically to save state that can be recovered if the agent
        restarts. State expires after 30 minutes by default.

        Returns:
            True if persisted successfully

        Raises:
            RuntimeError: If no short-term memory configured

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable state persistence.",
            )

        state_data = {
            "trust_level": self.collaboration_state.trust_level,
            "successful_interventions": self.collaboration_state.successful_interventions,
            "failed_interventions": self.collaboration_state.failed_interventions,
            "total_interactions": self.collaboration_state.total_interactions,
            "current_empathy_level": self.current_empathy_level,
            "session_start": self.collaboration_state.session_start.isoformat(),
            "trust_trajectory": self.collaboration_state.trust_trajectory[-100:],  # Last 100
        }
        return self.short_term_memory.stash(
            f"collaboration_state_{self.session_id}",
            state_data,
            self.credentials,
        )

    def restore_collaboration_state(self, session_id: str | None = None) -> bool:
        """Restore collaboration state from short-term memory.

        Use to recover state after agent restart or to continue a previous
        session.

        Args:
            session_id: Session to restore, or None for current session

        Returns:
            True if state was found and restored

        Raises:
            RuntimeError: If no short-term memory configured

        """
        if self.short_term_memory is None:
            raise RuntimeError(
                "No short-term memory configured. Pass short_term_memory to __init__ "
                "to enable state persistence.",
            )

        sid = session_id or self.session_id
        state_data = self.short_term_memory.retrieve(
            f"collaboration_state_{sid}",
            self.credentials,
        )

        if state_data is None:
            return False

        # Restore state
        self.collaboration_state.trust_level = state_data.get("trust_level", 0.5)
        self.collaboration_state.successful_interventions = state_data.get(
            "successful_interventions",
            0,
        )
        self.collaboration_state.failed_interventions = state_data.get("failed_interventions", 0)
        self.collaboration_state.total_interactions = state_data.get("total_interactions", 0)
        self.current_empathy_level = state_data.get("current_empathy_level", 1)
        self.collaboration_state.trust_trajectory = state_data.get("trust_trajectory", [])

        self.logger.info(
            f"Restored collaboration state from session {sid}",
            extra={
                "user_id": self.user_id,
                "restored_trust_level": self.collaboration_state.trust_level,
                "restored_interactions": self.collaboration_state.total_interactions,
            },
        )

        return True

    def get_memory_stats(self) -> dict | None:
        """Get statistics about the short-term memory system.

        Returns:
            Dict with memory usage, key counts, mode, or None if not configured

        """
        if self.short_term_memory is None:
            return None
        return self.short_term_memory.get_stats()
