"""Redis Memory Coordination for Attune AI

Coordination features for RedisShortTermMemory:
- Conflict negotiation (create, get, resolve)
- Coordination signals (send, receive)
- Session management (create, join, get)

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .memory.types import (
    AgentCredentials,
    ConflictContext,
    TTLStrategy,
)


class ConflictNegotiationMixin:
    """Mixin providing conflict negotiation operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, _delete, and PREFIX_CONFLICT.
    """

    def create_conflict_context(
        self,
        conflict_id: str,
        positions: dict[str, Any],
        interests: dict[str, list[str]],
        credentials: AgentCredentials,
        batna: str | None = None,
    ) -> ConflictContext:
        """Create context for principled negotiation

        Per Getting to Yes framework:
        - Separate positions from interests
        - Define BATNA before negotiating

        Args:
            conflict_id: Unique conflict identifier
            positions: agent_id -> their stated position
            interests: agent_id -> underlying interests
            credentials: Must be CONTRIBUTOR or higher
            batna: Best Alternative to Negotiated Agreement

        Returns:
            ConflictContext for resolution

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot create conflict context. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        context = ConflictContext(
            conflict_id=conflict_id,
            positions=positions,
            interests=interests,
            batna=batna,
        )

        key = f"{self.PREFIX_CONFLICT}{conflict_id}"
        self._set(
            key,
            json.dumps(context.to_dict()),
            TTLStrategy.CONFLICT_CONTEXT.value,
        )

        return context

    def get_conflict_context(
        self,
        conflict_id: str,
        credentials: AgentCredentials,
    ) -> ConflictContext | None:
        """Retrieve conflict context

        Args:
            conflict_id: Conflict identifier
            credentials: Any tier can read

        Returns:
            ConflictContext or None

        """
        key = f"{self.PREFIX_CONFLICT}{conflict_id}"
        raw = self._get(key)

        if raw is None:
            return None

        return ConflictContext.from_dict(json.loads(raw))

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Mark conflict as resolved

        Args:
            conflict_id: Conflict to resolve
            resolution: How it was resolved
            credentials: Must be VALIDATOR or higher

        Returns:
            True if resolved

        """
        if not credentials.can_validate():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot resolve conflicts. "
                "Requires VALIDATOR tier or higher.",
            )

        context = self.get_conflict_context(conflict_id, credentials)
        if context is None:
            return False

        context.resolved = True
        context.resolution = resolution

        key = f"{self.PREFIX_CONFLICT}{conflict_id}"
        # Keep resolved conflicts longer for audit
        self._set(
            key,
            json.dumps(context.to_dict()),
            TTLStrategy.CONFLICT_CONTEXT.value,
        )
        return True


class CoordinationSignalsMixin:
    """Mixin providing coordination signal operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, _keys, and PREFIX_COORDINATION.
    """

    def send_signal(
        self,
        signal_type: str,
        data: Any,
        credentials: AgentCredentials,
        target_agent: str | None = None,
    ) -> bool:
        """Send coordination signal to other agents

        Args:
            signal_type: Type of signal (e.g., "ready",
                "blocking", "complete")
            data: Signal payload
            credentials: Must be CONTRIBUTOR or higher
            target_agent: Specific agent to signal
                (None = broadcast)

        Returns:
            True if sent

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot send signals. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        target = target_agent or "broadcast"
        key = f"{self.PREFIX_COORDINATION}{signal_type}:" f"{credentials.agent_id}:{target}"
        payload = {
            "signal_type": signal_type,
            "from_agent": credentials.agent_id,
            "to_agent": target_agent,
            "data": data,
            "sent_at": datetime.now().isoformat(),
        }
        return self._set(
            key,
            json.dumps(payload),
            TTLStrategy.COORDINATION.value,
        )

    def receive_signals(
        self,
        credentials: AgentCredentials,
        signal_type: str | None = None,
    ) -> list[dict]:
        """Receive coordination signals

        Args:
            credentials: Agent receiving signals
            signal_type: Filter by signal type (optional)

        Returns:
            List of signals

        """
        if signal_type:
            pattern = f"{self.PREFIX_COORDINATION}{signal_type}:*:" f"{credentials.agent_id}"
        else:
            pattern = f"{self.PREFIX_COORDINATION}*:" f"{credentials.agent_id}"

        # Also get broadcasts
        broadcast_pattern = f"{self.PREFIX_COORDINATION}*:*:broadcast"

        keys = set(self._keys(pattern)) | set(self._keys(broadcast_pattern))
        signals = []

        for key in keys:
            raw = self._get(key)
            if raw:
                signals.append(json.loads(raw))

        return signals


class SessionManagementMixin:
    """Mixin providing session management operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, and PREFIX_SESSION.
    """

    def create_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
        metadata: dict | None = None,
    ) -> bool:
        """Create a collaboration session

        Args:
            session_id: Unique session identifier
            credentials: Session creator
            metadata: Optional session metadata

        Returns:
            True if created

        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        payload = {
            "session_id": session_id,
            "created_by": credentials.agent_id,
            "created_at": datetime.now().isoformat(),
            "participants": [credentials.agent_id],
            "metadata": metadata or {},
        }
        return self._set(
            key,
            json.dumps(payload),
            TTLStrategy.SESSION.value,
        )

    def join_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Join an existing session

        Args:
            session_id: Session to join
            credentials: Joining agent

        Returns:
            True if joined

        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        raw = self._get(key)

        if raw is None:
            return False

        payload = json.loads(raw)
        if credentials.agent_id not in payload["participants"]:
            payload["participants"].append(credentials.agent_id)

        return self._set(
            key,
            json.dumps(payload),
            TTLStrategy.SESSION.value,
        )

    def get_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> dict | None:
        """Get session information

        Args:
            session_id: Session identifier
            credentials: Any participant can read

        Returns:
            Session data or None

        """
        key = f"{self.PREFIX_SESSION}{session_id}"
        raw = self._get(key)

        if raw is None:
            return None

        result: dict = json.loads(raw)
        return result
