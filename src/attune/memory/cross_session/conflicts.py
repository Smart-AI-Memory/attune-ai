"""Conflict resolution strategies for cross-session coordination.

Implements priority-based, first-write-wins, and last-write-wins
strategies for resolving resource contention between distributed
agents.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import ConflictResult, ConflictStrategy, SessionInfo

if TYPE_CHECKING:
    from attune.memory.short_term import AccessTier


def resolve_by_priority(
    agent_id: str,
    access_tier: AccessTier,
    session_info: SessionInfo,
    resource_key: str,
    other_session: SessionInfo | None,
) -> ConflictResult:
    """Resolve conflict using priority (access tier).

    Args:
        agent_id: This agent's ID.
        access_tier: This agent's access tier.
        session_info: This agent's session info.
        resource_key: Key of the contested resource.
        other_session: The other session's info, or None.

    Returns:
        ConflictResult indicating winner and loser.

    """
    my_tier = access_tier.value
    other_tier = other_session.access_tier.value if other_session else 0
    other_id = other_session.agent_id if other_session else "unknown"

    if my_tier > other_tier:
        winner, loser = agent_id, other_id
        reason = (
            f"Higher tier ({access_tier.name} > "
            f"{other_session.access_tier.name if other_session else 'N/A'})"
        )
    elif my_tier < other_tier:
        winner, loser = other_id, agent_id
        reason = (
            f"Higher tier ("
            f"{other_session.access_tier.name if other_session else 'N/A'}"
            f" > {access_tier.name})"
        )
    # Equal tier - use timestamp (first write wins)
    elif other_session and other_session.started_at < session_info.started_at:
        winner, loser = other_id, agent_id
        reason = "Equal tier, earlier session wins"
    else:
        winner, loser = agent_id, other_id
        reason = "Equal tier, earlier session wins"

    return ConflictResult(
        winner_agent_id=winner,
        loser_agent_id=loser,
        resource_key=resource_key,
        strategy_used=ConflictStrategy.PRIORITY_BASED,
        reason=reason,
    )


def resolve_first_write(
    agent_id: str,
    client: Any,
    resource_key: str,
    other_session: SessionInfo | None,
) -> ConflictResult:
    """Resolve conflict using first-write-wins.

    Args:
        agent_id: This agent's ID.
        client: Redis client (may be None).
        resource_key: Key of the contested resource.
        other_session: The other session's info, or None.

    Returns:
        ConflictResult indicating winner and loser.

    """
    if client is None:
        return ConflictResult(
            winner_agent_id=agent_id,
            loser_agent_id=(other_session.agent_id if other_session else "unknown"),
            resource_key=resource_key,
            strategy_used=ConflictStrategy.FIRST_WRITE_WINS,
            reason="No Redis connection - local wins",
        )

    # Try to get lock on resource
    lock_key = f"empathy:lock:{resource_key}"
    # One atomic command: a crash between SETNX and EXPIRE would leave an
    # immortal lock and hand every later conflict to a dead agent
    # (library-review H2).
    acquired = client.set(lock_key, agent_id, nx=True, ex=300)  # 5 minute lock

    if acquired:
        winner = agent_id
        loser = other_session.agent_id if other_session else "unknown"
        reason = "First to acquire lock"
    else:
        current_owner = client.get(lock_key)
        if isinstance(current_owner, bytes):
            current_owner = current_owner.decode()
        winner = current_owner or "unknown"
        loser = agent_id
        reason = "Lock already held"

    return ConflictResult(
        winner_agent_id=winner,
        loser_agent_id=loser,
        resource_key=resource_key,
        strategy_used=ConflictStrategy.FIRST_WRITE_WINS,
        reason=reason,
    )


def resolve_last_write(
    agent_id: str,
    resource_key: str,
    other_session: SessionInfo | None,
) -> ConflictResult:
    """Resolve conflict using last-write-wins.

    Args:
        agent_id: This agent's ID.
        resource_key: Key of the contested resource.
        other_session: The other session's info, or None.

    Returns:
        ConflictResult indicating winner and loser.

    """
    return ConflictResult(
        winner_agent_id=agent_id,
        loser_agent_id=(other_session.agent_id if other_session else "unknown"),
        resource_key=resource_key,
        strategy_used=ConflictStrategy.LAST_WRITE_WINS,
        reason="Last write wins - current writer takes precedence",
    )
