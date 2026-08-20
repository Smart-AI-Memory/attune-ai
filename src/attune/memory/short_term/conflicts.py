"""Conflict negotiation for multi-agent collaboration.

This module provides principled negotiation support per "Getting to Yes":
- Separate positions from interests
- Define BATNA before negotiating
- Track resolution outcomes

Key Prefix: PREFIX_CONFLICT = "empathy:conflict:"

Classes:
    ConflictNegotiation: Conflict context and resolution operations

Example:
    >>> from attune.memory.short_term.conflicts import ConflictNegotiation
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> negotiation = ConflictNegotiation(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> context = negotiation.create_conflict_context(
    ...     "conflict_1",
    ...     positions={"agent_1": "Use Redis", "agent_2": "Use SQLite"},
    ...     interests={"agent_1": ["speed", "scale"], "agent_2": ["simplicity"]},
    ...     credentials=creds,
    ... )

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.types import (
    AgentCredentials,
    ConflictContext,
    TTLStrategy,
    parse_stored_record,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class ConflictNegotiation:
    """Conflict context and resolution operations.

    Implements principled negotiation per "Getting to Yes" framework:
    - Separate positions from interests
    - Define BATNA (Best Alternative to Negotiated Agreement)
    - Track resolution outcomes for learning

    The class is designed to be composed with BaseOperations
    for dependency injection.

    Attributes:
        PREFIX_CONFLICT: Key prefix for conflict context namespace

    Example:
        >>> negotiation = ConflictNegotiation(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> context = negotiation.create_conflict_context(...)
        >>> negotiation.resolve_conflict("conflict_1", "Chose Redis", validator_creds)

    """

    PREFIX_CONFLICT = "empathy:conflict:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize conflict negotiation operations.

        Args:
            base: BaseOperations instance for storage access

        """
        self._base = base

    def create_conflict_context(
        self,
        conflict_id: str,
        positions: dict[str, Any],
        interests: dict[str, list[str]],
        credentials: AgentCredentials,
        batna: str | None = None,
    ) -> ConflictContext:
        """Create context for principled negotiation.

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

        Raises:
            ValueError: If conflict_id is empty
            TypeError: If positions or interests are not dicts
            PermissionError: If credentials lack permission

        Example:
            >>> context = negotiation.create_conflict_context(
            ...     "conflict_1",
            ...     positions={"a1": "Redis", "a2": "SQLite"},
            ...     interests={"a1": ["speed"], "a2": ["simplicity"]},
            ...     credentials=creds,
            ...     batna="Use file-based storage",
            ... )

        """
        # Pattern 1: String ID validation
        if not conflict_id or not conflict_id.strip():
            raise ValueError(f"conflict_id cannot be empty. Got: {conflict_id!r}")

        # Pattern 5: Type validation
        if not isinstance(positions, dict):
            raise TypeError(f"positions must be dict, got {type(positions).__name__}")
        if not isinstance(interests, dict):
            raise TypeError(f"interests must be dict, got {type(interests).__name__}")

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
        self._base._set(
            key,
            json.dumps(context.to_dict()),
            TTLStrategy.CONFLICT_CONTEXT.value,
        )

        logger.info(
            "conflict_context_created",
            conflict_id=conflict_id,
            agent_count=len(positions),
            has_batna=batna is not None,
        )

        return context

    def get_conflict_context(
        self,
        conflict_id: str,
        credentials: AgentCredentials,
    ) -> ConflictContext | None:
        """Retrieve conflict context.

        Args:
            conflict_id: Conflict identifier
            credentials: Any tier can read

        Returns:
            ConflictContext or None if not found

        Raises:
            ValueError: If conflict_id is empty

        Example:
            >>> context = negotiation.get_conflict_context("conflict_1", creds)
            >>> if context:
            ...     print(f"BATNA: {context.batna}")

        """
        # Pattern 1: String ID validation
        if not conflict_id or not conflict_id.strip():
            raise ValueError(f"conflict_id cannot be empty. Got: {conflict_id!r}")

        key = f"{self.PREFIX_CONFLICT}{conflict_id}"
        raw = self._base._get(key)

        if raw is None:
            return None

        return parse_stored_record(ConflictContext, raw, key=key)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Mark conflict as resolved.

        Args:
            conflict_id: Conflict to resolve
            resolution: How it was resolved
            credentials: Must be VALIDATOR or higher

        Returns:
            True if resolved

        Raises:
            PermissionError: If credentials lack validation access

        Example:
            >>> negotiation.resolve_conflict(
            ...     "conflict_1",
            ...     "Chose Redis for better scaling",
            ...     validator_creds,
            ... )
            True

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
        self._base._set(key, json.dumps(context.to_dict()), TTLStrategy.CONFLICT_CONTEXT.value)

        logger.info(
            "conflict_resolved",
            conflict_id=conflict_id,
            agent_id=credentials.agent_id,
        )

        return True

    def list_active_conflicts(
        self,
        credentials: AgentCredentials,
    ) -> list[ConflictContext]:
        """List all active (unresolved) conflicts.

        Args:
            credentials: Any tier can read

        Returns:
            List of unresolved conflict contexts

        """
        pattern = f"{self.PREFIX_CONFLICT}*"
        keys = self._base._keys(pattern)
        conflicts = []

        for raw in self._base._mget(keys):
            context = parse_stored_record(ConflictContext, raw, key=pattern) if raw else None
            if context is not None and not context.resolved:
                conflicts.append(context)

        return conflicts
