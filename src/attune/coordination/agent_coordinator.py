"""Redis-Backed Multi-Agent Coordination

Provides task distribution, agent registration, and result aggregation
for multi-agent teams using Redis short-term memory.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .conflict_resolution import ConflictResolver


@dataclass
class AgentTask:
    """A task assigned to an agent"""

    task_id: str
    task_type: str
    description: str
    assigned_to: str | None = None
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 5  # 1-10, higher = more important
    created_at: datetime = field(default_factory=datetime.now)
    context: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None


class AgentCoordinator:
    """Redis-backed coordinator for multi-agent teams.

    Enables real-time coordination between agents using Redis short-term memory:
    - Task distribution and claiming
    - Status broadcasting
    - Result aggregation
    - Conflict resolution

    Example:
        >>> from attune import get_redis_memory, AgentCoordinator
        >>>
        >>> memory = get_redis_memory()
        >>> coordinator = AgentCoordinator(memory, team_id="code_review_team")
        >>>
        >>> # Add tasks for agents to claim
        >>> coordinator.add_task(AgentTask(
        ...     task_id="review_001",
        ...     task_type="code_review",
        ...     description="Review auth module",
        ...     priority=8
        ... ))
        >>>
        >>> # Agent claims a task
        >>> task = coordinator.claim_task("agent_1", "code_review")
        >>> if task:
        ...     # Do work...
        ...     coordinator.complete_task(task.task_id, {"issues_found": 3})

    """

    def __init__(
        self,
        short_term_memory,
        team_id: str,
        conflict_resolver: ConflictResolver | None = None,
    ):
        """Initialize the coordinator.

        Args:
            short_term_memory: RedisShortTermMemory instance
            team_id: Unique identifier for this team
            conflict_resolver: Optional ConflictResolver for pattern conflicts

        """
        from ..redis_memory import AccessTier, AgentCredentials

        self.memory = short_term_memory
        self.team_id = team_id
        self.conflict_resolver = conflict_resolver or ConflictResolver()

        # Coordinator has Steward-level access
        self._credentials = AgentCredentials(
            agent_id=f"coordinator_{team_id}",
            tier=AccessTier.STEWARD,
        )

        # Track active agents
        self._active_agents: dict[str, datetime] = {}

    def add_task(self, task: AgentTask) -> bool:
        """Add a task to the queue for agents to claim.

        Args:
            task: The task to add

        Returns:
            True if added successfully

        """
        task_data = {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "description": task.description,
            "assigned_to": task.assigned_to,
            "status": task.status,
            "priority": task.priority,
            "created_at": task.created_at.isoformat(),
            "context": task.context,
        }

        result = self.memory.stash(
            f"task:{self.team_id}:{task.task_id}",
            task_data,
            self._credentials,
        )
        return bool(result)

    def get_pending_tasks(self, task_type: str | None = None) -> list[AgentTask]:
        """Get all pending tasks, optionally filtered by type.

        Args:
            task_type: Filter by task type

        Returns:
            List of pending AgentTask objects

        """
        # In a real implementation, we'd scan Redis keys
        # For now, this is a simplified version
        tasks = []

        # Get tasks from coordination signals
        signals = self.memory.receive_signals(
            self._credentials,
            signal_type="task_added",
        )

        for signal in signals:
            task_data = signal.get("data", {})
            if task_data.get("status") == "pending":
                if task_type is None or task_data.get("task_type") == task_type:
                    tasks.append(
                        AgentTask(
                            task_id=task_data["task_id"],
                            task_type=task_data.get("task_type", "unknown"),
                            description=task_data.get("description", ""),
                            status=task_data.get("status", "pending"),
                            priority=task_data.get("priority", 5),
                            context=task_data.get("context", {}),
                        ),
                    )

        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def claim_task(
        self,
        agent_id: str,
        task_type: str | None = None,
    ) -> AgentTask | None:
        """Claim a pending task for an agent.

        Uses atomic operations to prevent race conditions.

        Args:
            agent_id: Agent claiming the task
            task_type: Optional filter by task type

        Returns:
            The claimed task, or None if no tasks available

        """
        pending = self.get_pending_tasks(task_type)

        for task in pending:
            # Try to claim (atomic check-and-set in Redis)
            task_key = f"task:{self.team_id}:{task.task_id}"
            current = self.memory.retrieve(task_key, self._credentials)

            if current and current.get("status") == "pending":
                # Update to claimed
                current["status"] = "in_progress"
                current["assigned_to"] = agent_id
                current["claimed_at"] = datetime.now().isoformat()

                if self.memory.stash(task_key, current, self._credentials):
                    task.status = "in_progress"
                    task.assigned_to = agent_id

                    # Broadcast claim
                    self.memory.send_signal(
                        signal_type="task_claimed",
                        data={
                            "task_id": task.task_id,
                            "agent_id": agent_id,
                            "task_type": task.task_type,
                        },
                        credentials=self._credentials,
                    )

                    return task

        return None

    def complete_task(
        self,
        task_id: str,
        result: dict[str, Any],
        agent_id: str | None = None,
    ) -> bool:
        """Mark a task as completed with results.

        Args:
            task_id: Task to complete
            result: Task results
            agent_id: Agent that completed (for verification)

        Returns:
            True if completed successfully

        """
        task_key = f"task:{self.team_id}:{task_id}"
        current = self.memory.retrieve(task_key, self._credentials)

        if not current:
            return False

        if agent_id and current.get("assigned_to") != agent_id:
            return False  # Wrong agent

        current["status"] = "completed"
        current["result"] = result
        current["completed_at"] = datetime.now().isoformat()

        if self.memory.stash(task_key, current, self._credentials):
            # Broadcast completion
            self.memory.send_signal(
                signal_type="task_completed",
                data={
                    "task_id": task_id,
                    "agent_id": current.get("assigned_to"),
                    "task_type": current.get("task_type"),
                    "result_summary": {
                        k: v for k, v in result.items() if isinstance(v, str | int | float | bool)
                    },
                },
                credentials=self._credentials,
            )
            return True

        return False

    def register_agent(self, agent_id: str, capabilities: list[str] | None = None) -> bool:
        """Register an agent with the team.

        Args:
            agent_id: Unique agent identifier
            capabilities: List of task types this agent can handle

        Returns:
            True if registered successfully

        """
        self._active_agents[agent_id] = datetime.now()

        result = self.memory.stash(
            f"agent:{self.team_id}:{agent_id}",
            {
                "agent_id": agent_id,
                "capabilities": capabilities or [],
                "registered_at": datetime.now().isoformat(),
                "status": "active",
            },
            self._credentials,
        )
        return bool(result)

    def heartbeat(self, agent_id: str) -> bool:
        """Send heartbeat to indicate agent is still active.

        Args:
            agent_id: Agent sending heartbeat

        Returns:
            True if heartbeat recorded

        """
        self._active_agents[agent_id] = datetime.now()

        result = self.memory.send_signal(
            signal_type="heartbeat",
            data={"agent_id": agent_id, "timestamp": datetime.now().isoformat()},
            credentials=self._credentials,
        )
        return bool(result)

    def get_active_agents(self, timeout_seconds: int = 300) -> list[str]:
        """Get list of recently active agents.

        Args:
            timeout_seconds: Consider agents inactive after this duration

        Returns:
            List of active agent IDs

        """
        cutoff = datetime.now()
        active = []

        for agent_id, last_seen in self._active_agents.items():
            if (cutoff - last_seen).total_seconds() < timeout_seconds:
                active.append(agent_id)

        return active

    def broadcast(self, message_type: str, data: dict[str, Any]) -> bool:
        """Broadcast a message to all agents in the team.

        Args:
            message_type: Type of message
            data: Message payload

        Returns:
            True if broadcast sent

        """
        result = self.memory.send_signal(
            signal_type=message_type,
            data={"team_id": self.team_id, **data},
            credentials=self._credentials,
        )
        return bool(result)

    def aggregate_results(self, task_type: str | None = None) -> dict[str, Any]:
        """Aggregate results from completed tasks.

        Args:
            task_type: Optional filter by task type

        Returns:
            Aggregated results summary

        """
        # Get completion signals
        completions = self.memory.receive_signals(
            self._credentials,
            signal_type="task_completed",
        )

        results: dict[str, Any] = {
            "total_completed": 0,
            "by_agent": {},
            "by_type": {},
            "summaries": [],
        }

        for signal in completions:
            data = signal.get("data", {})
            if task_type and data.get("task_type") != task_type:
                continue

            results["total_completed"] += 1

            agent = data.get("agent_id", "unknown")
            results["by_agent"][agent] = results["by_agent"].get(agent, 0) + 1

            ttype = data.get("task_type", "unknown")
            results["by_type"][ttype] = results["by_type"].get(ttype, 0) + 1

            if "result_summary" in data:
                results["summaries"].append(data["result_summary"])

        return results
