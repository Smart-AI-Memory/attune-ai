"""Collaboration session management.

This module manages multi-agent collaboration sessions:
- Create: Start a new collaboration session
- Join: Add agents to existing session
- Get: Retrieve session information

Key Prefix: PREFIX_SESSION = "empathy:session:"

Classes:
    SessionManager: Collaboration session operations

Example:
    >>> from attune.memory.short_term.sessions import SessionManager
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> sessions = SessionManager(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> sessions.create_session("session_1", creds, {"topic": "refactoring"})
    >>> sessions.join_session("session_1", other_agent_creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.types import (
    AgentCredentials,
    TTLStrategy,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class SessionManager:
    """Collaboration session operations.

    Manages multi-agent collaboration sessions including creation,
    joining, and retrieval. Sessions track participants and metadata.

    The class is designed to be composed with BaseOperations
    for dependency injection.

    Attributes:
        PREFIX_SESSION: Key prefix for session namespace

    Example:
        >>> sessions = SessionManager(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> sessions.create_session("session_1", creds)
        True
        >>> info = sessions.get_session("session_1", creds)

    """

    PREFIX_SESSION = "empathy:session:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize session manager.

        Args:
            base: BaseOperations instance for storage access

        """
        self._base = base

    def create_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
        metadata: dict | None = None,
    ) -> bool:
        """Create a collaboration session.

        Args:
            session_id: Unique session identifier
            credentials: Session creator
            metadata: Optional session metadata

        Returns:
            True if created

        Raises:
            ValueError: If session_id is empty
            TypeError: If metadata is not dict

        Example:
            >>> sessions.create_session(
            ...     "session_1",
            ...     creds,
            ...     metadata={"topic": "code review"},
            ... )
            True

        """
        # Pattern 1: String ID validation
        if not session_id or not session_id.strip():
            raise ValueError(f"session_id cannot be empty. Got: {session_id!r}")

        # Pattern 5: Type validation
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError(f"metadata must be dict, got {type(metadata).__name__}")

        key = f"{self.PREFIX_SESSION}{session_id}"
        payload = {
            "session_id": session_id,
            "created_by": credentials.agent_id,
            "created_at": datetime.now().isoformat(),
            "participants": [credentials.agent_id],
            "metadata": metadata or {},
        }

        success = self._base._set(key, json.dumps(payload), TTLStrategy.SESSION.value)

        if success:
            logger.info(
                "session_created",
                session_id=session_id,
                created_by=credentials.agent_id,
            )

        return success

    def join_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Join an existing session.

        Args:
            session_id: Session to join
            credentials: Joining agent

        Returns:
            True if joined

        Raises:
            ValueError: If session_id is empty

        Example:
            >>> sessions.join_session("session_1", agent2_creds)
            True

        """
        # Pattern 1: String ID validation
        if not session_id or not session_id.strip():
            raise ValueError(f"session_id cannot be empty. Got: {session_id!r}")

        key = f"{self.PREFIX_SESSION}{session_id}"
        raw = self._base._get(key)

        if raw is None:
            return False

        payload = json.loads(raw)
        if credentials.agent_id not in payload["participants"]:
            payload["participants"].append(credentials.agent_id)
            logger.info(
                "session_joined",
                session_id=session_id,
                agent_id=credentials.agent_id,
            )

        return self._base._set(key, json.dumps(payload), TTLStrategy.SESSION.value)

    def get_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> dict[str, Any] | None:
        """Get session information.

        Args:
            session_id: Session identifier
            credentials: Any participant can read

        Returns:
            Session data or None if not found

        Example:
            >>> info = sessions.get_session("session_1", creds)
            >>> if info:
            ...     print(f"Participants: {info['participants']}")

        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        raw = self._base._get(key)

        if raw is None:
            return None

        result: dict[str, Any] = json.loads(raw)
        return result

    def leave_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Leave a session.

        Args:
            session_id: Session to leave
            credentials: Leaving agent

        Returns:
            True if left successfully

        """
        if not session_id or not session_id.strip():
            raise ValueError(f"session_id cannot be empty. Got: {session_id!r}")

        key = f"{self.PREFIX_SESSION}{session_id}"
        raw = self._base._get(key)

        if raw is None:
            return False

        payload = json.loads(raw)
        if credentials.agent_id in payload["participants"]:
            payload["participants"].remove(credentials.agent_id)
            logger.info(
                "session_left",
                session_id=session_id,
                agent_id=credentials.agent_id,
            )
            return self._base._set(key, json.dumps(payload), TTLStrategy.SESSION.value)

        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all active sessions.

        Returns:
            List of session data dicts

        """
        pattern = f"{self.PREFIX_SESSION}*"
        keys = self._base._keys(pattern)
        sessions = []

        for raw in self._base._mget(keys):
            if raw:
                sessions.append(json.loads(raw))

        return sessions
