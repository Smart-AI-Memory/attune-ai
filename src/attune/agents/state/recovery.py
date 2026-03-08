"""Agent restart recovery from persistent state.

Detects interrupted agent executions and provides recovery options
including checkpoint restoration and abandoned execution cleanup.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from .models import AgentStateRecord
from .store import AgentStateStore

logger = logging.getLogger(__name__)


class AgentRecoveryManager:
    """Handles agent restart recovery from persistent state.

    On startup, checks for agents with executions in 'running' status
    that never completed (indicating a crash or interruption) and
    provides recovery options.

    Args:
        state_store: AgentStateStore for reading/writing state

    Example:
        >>> recovery = AgentRecoveryManager(state_store)
        >>> interrupted = recovery.find_interrupted_agents()
        >>> for agent in interrupted:
        ...     checkpoint = recovery.recover_agent(agent.agent_id)
        ...     if checkpoint:
        ...         resume_from(checkpoint)
        ...     else:
        ...         recovery.mark_abandoned(agent.agent_id)

    """

    def __init__(self, state_store: AgentStateStore) -> None:
        """Initialize the recovery manager.

        Args:
            state_store: State store to query for interrupted agents.
        """
        self._store = state_store

    def find_interrupted_agents(self) -> list[AgentStateRecord]:
        """Find agents with executions that never completed.

        Returns:
            List of AgentStateRecord with at least one 'running' execution

        """
        interrupted = []
        for record in self._store.get_all_agents():
            has_running = any(e.status == "running" for e in record.execution_history)
            if has_running:
                interrupted.append(record)
        return interrupted

    def recover_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Get recovery data for an interrupted agent.

        Returns the last checkpoint if available, which can be used
        to resume execution from where it left off.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Checkpoint dict or None if no checkpoint exists

        """
        checkpoint = self._store.get_last_checkpoint(agent_id)
        if checkpoint:
            logger.info("Found checkpoint for agent %s", agent_id)
        else:
            logger.info("No checkpoint found for agent %s", agent_id)
        return checkpoint

    def mark_abandoned(self, agent_id: str) -> None:
        """Mark all running executions for an agent as interrupted.

        Use this when recovery is not possible and the executions
        should be recorded as failed.

        Args:
            agent_id: Unique agent identifier

        """
        record = self._store.get_agent_state(agent_id)
        if record is None:
            logger.warning("Agent %s not found in state store", agent_id)
            return

        now = datetime.now().isoformat()
        marked = 0
        for execution in record.execution_history:
            if execution.status == "running":
                execution.status = "interrupted"
                execution.completed_at = now
                execution.error = "Marked as interrupted by recovery manager"
                record.failed_executions += 1
                marked += 1

        if marked > 0:
            record.last_active = now
            self._store._save(record)
            logger.info(
                "Marked %d interrupted execution(s) for agent %s",
                marked,
                agent_id,
            )
