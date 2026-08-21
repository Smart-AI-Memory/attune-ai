"""Deprecated — use attune_redis for coordination.

Superseded by attune_redis.AMSMemoryBackend (the Redis Agent Memory Server integration). Retained — attune is aligning on Redis + Anthropic Claude, so there is no planned removal. Migration path: docs/migration/redis-plugin-migration.md

Legacy coordination mixins kept for backward compatibility.
New code should use ``attune_redis.signals.RedisSignalBus``.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import warnings

warnings.warn(
    "attune.redis_memory_coordination is deprecated. "
    "Use attune_redis.signals.RedisSignalBus instead.",
    DeprecationWarning,
    stacklevel=2,
)

import json  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import TYPE_CHECKING, Any  # noqa: E402

from .memory.types import (  # noqa: E402
    AgentCredentials,
    ConflictContext,
    TTLStrategy,
    parse_stored_record,
)


class ConflictNegotiationMixin:
    """Mixin providing conflict negotiation operations.

    Must be combined with RedisStorageBase (or a subclass)
    to access _get, _set, _delete, and PREFIX_CONFLICT.
    """

    PREFIX_CONFLICT: str

    if TYPE_CHECKING:

        def _get(self, key: str) -> str | None: ...
        def _set(self, key: str, value: str, ttl: int | None = None) -> bool: ...
        def _delete(self, key: str) -> bool: ...

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

        # Deserialize-here / subscript-there (library-review I-4): a value
        # that parses to a LIST makes from_dict raise TypeError from inside
        # the call, past a caller whose except tuple lists only
        # JSONDecodeError. parse_stored_record returns None instead.
        return parse_stored_record(ConflictContext, raw, key=key)

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

    PREFIX_COORDINATION: str

    if TYPE_CHECKING:

        def _get(self, key: str) -> str | None: ...
        def _set(self, key: str, value: str, ttl: int | None = None) -> bool: ...
        def _keys(self, pattern: str) -> list[str]: ...

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
        key = f"{self.PREFIX_COORDINATION}{signal_type}:{credentials.agent_id}:{target}"
        payload = {
            "signal_type": signal_type,
            "from_agent": credentials.agent_id,
            "to_agent": target_agent,
            "data": data,
            "sent_at": datetime.now().isoformat(),
        }
        return bool(
            self._set(
                key,
                json.dumps(payload),
                300,  # 5 minutes (COORDINATION TTL removed from enum in v5.0)
            )
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
            pattern = f"{self.PREFIX_COORDINATION}{signal_type}:*:{credentials.agent_id}"
        else:
            pattern = f"{self.PREFIX_COORDINATION}*:{credentials.agent_id}"

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

    PREFIX_SESSION: str

    if TYPE_CHECKING:

        def _get(self, key: str) -> str | None: ...
        def _set(self, key: str, value: str, ttl: int | None = None) -> bool: ...

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
        return bool(
            self._set(
                key,
                json.dumps(payload),
                TTLStrategy.SESSION.value,
            )
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

        return bool(
            self._set(
                key,
                json.dumps(payload),
                TTLStrategy.SESSION.value,
            )
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
