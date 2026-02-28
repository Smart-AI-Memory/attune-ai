"""Team Session for Collaborative Multi-Agent Work

Provides a collaborative session abstraction for multiple agents working
together on a shared task, with shared context and signaling.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from typing import Any


class TeamSession:
    """A collaborative session for multiple agents working together.

    Example:
        >>> from attune import get_redis_memory, TeamSession
        >>>
        >>> memory = get_redis_memory()
        >>> session = TeamSession(
        ...     memory,
        ...     session_id="pr_review_42",
        ...     purpose="Review PR #42"
        ... )
        >>>
        >>> session.add_agent("security_agent")
        >>> session.add_agent("performance_agent")
        >>>
        >>> # Share context between agents
        >>> session.share("analysis_scope", {"files": 15, "lines": 500})
        >>>
        >>> # Get context from session
        >>> scope = session.get("analysis_scope")

    """

    def __init__(
        self,
        short_term_memory,
        session_id: str,
        purpose: str = "",
    ):
        """Create or join a team session.

        Args:
            short_term_memory: RedisShortTermMemory instance
            session_id: Unique session identifier
            purpose: Description of what this session is for

        """
        from ..memory.types import AccessTier, AgentCredentials

        self.memory = short_term_memory
        self.session_id = session_id
        self.purpose = purpose

        self._credentials = AgentCredentials(
            agent_id=f"session_{session_id}",
            tier=AccessTier.CONTRIBUTOR,
        )

        # Initialize session in Redis
        self.memory.create_session(
            session_id=session_id,
            credentials=self._credentials,
            metadata={"purpose": purpose, "created_at": datetime.now().isoformat()},
        )

    def add_agent(self, agent_id: str) -> bool:
        """Add an agent to this session."""
        from ..memory.types import AccessTier, AgentCredentials

        agent_creds = AgentCredentials(agent_id=agent_id, tier=AccessTier.CONTRIBUTOR)
        return bool(self.memory.join_session(self.session_id, agent_creds))

    def get_info(self) -> dict[str, Any] | None:
        """Get session info including participants."""
        result = self.memory.get_session(self.session_id, self._credentials)
        return dict(result) if result else None

    def share(self, key: str, data: Any) -> bool:
        """Share data with all agents in the session.

        Args:
            key: Unique key for this data
            data: Any JSON-serializable data

        Returns:
            True if shared successfully

        """
        return bool(
            self.memory.stash(
                f"session:{self.session_id}:{key}",
                data,
                self._credentials,
            ),
        )

    def get(self, key: str) -> Any | None:
        """Get shared data from the session.

        Args:
            key: Key of the shared data

        Returns:
            The data, or None if not found

        """
        return self.memory.retrieve(
            f"session:{self.session_id}:{key}",
            self._credentials,
        )

    def signal(self, signal_type: str, data: dict[str, Any]) -> bool:
        """Send a signal to session participants.

        Args:
            signal_type: Type of signal
            data: Signal payload

        Returns:
            True if sent

        """
        return bool(
            self.memory.send_signal(
                signal_type=signal_type,
                data={"session_id": self.session_id, **data},
                credentials=self._credentials,
            ),
        )

    def get_signals(self, signal_type: str | None = None) -> list[dict]:
        """Get signals from the session.

        Args:
            signal_type: Optional filter

        Returns:
            List of signals

        """
        result = self.memory.receive_signals(self._credentials, signal_type=signal_type)
        return list(result) if result else []
