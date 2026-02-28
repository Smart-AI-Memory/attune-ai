"""Task queue operations using Redis lists.

This module provides queue operations for task processing:
- Push: Add task to queue (LPUSH/RPUSH)
- Pop: Remove and return task (LPOP/BLPOP)
- Length: Get queue size
- Peek: View task without removing

Key Prefix: PREFIX_QUEUE = "queue:"

Use Cases:
- Background job queues
- Task distribution
- Work stealing patterns

Classes:
    QueueManager: Redis list operations for task queues

Example:
    >>> from attune.memory.short_term.queues import QueueManager
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> queues = QueueManager(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> queues.push("tasks", {"type": "analyze", "file": "main.py"}, creds)
    >>> task = queues.pop("tasks", creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class QueueManager:
    """Redis list operations for task queues.

    Provides FIFO queue operations using Redis lists for task
    distribution and background job processing.

    The class manages its own mock list storage for testing,
    composed with BaseOperations for Redis client access.

    Attributes:
        PREFIX_QUEUE: Key prefix for queue names

    Example:
        >>> queues = QueueManager(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> queues.push("analysis_tasks", {"file": "main.py"}, creds)
        >>> task = queues.pop("analysis_tasks", creds, timeout=5)

    """

    PREFIX_QUEUE = "queue:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize queue manager.

        Args:
            base: BaseOperations instance for Redis client access

        """
        self._base = base
        self._mock_lists: dict[str, list[str]] = {}

    def push(
        self,
        queue_name: str,
        task: dict,
        credentials: AgentCredentials,
        priority: bool = False,
    ) -> int:
        """Push a task to a queue.

        Args:
            queue_name: Name of the queue
            task: Task data
            credentials: Agent credentials (must be CONTRIBUTOR+)
            priority: If True, push to front (high priority)

        Returns:
            New queue length

        Raises:
            PermissionError: If credentials lack write access

        Example:
            >>> task = {"type": "analyze", "file": "main.py"}
            >>> queues.push("agent_tasks", task, creds)
            1

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot push to queue. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        full_queue = f"{self.PREFIX_QUEUE}{queue_name}"
        payload = json.dumps(
            {
                "task": task,
                "queued_by": credentials.agent_id,
                "queued_at": datetime.now().isoformat(),
            },
        )

        # Handle mock mode
        if self._base.use_mock:
            if full_queue not in self._mock_lists:
                self._mock_lists[full_queue] = []
            if priority:
                self._mock_lists[full_queue].insert(0, payload)
            else:
                self._mock_lists[full_queue].append(payload)
            return len(self._mock_lists[full_queue])

        # Handle real Redis client
        if self._base._client is None:
            return 0

        if priority:
            return int(self._base._client.lpush(full_queue, payload))
        return int(self._base._client.rpush(full_queue, payload))

    def pop(
        self,
        queue_name: str,
        credentials: AgentCredentials,
        timeout: int = 0,
    ) -> dict | None:
        """Pop a task from a queue.

        Args:
            queue_name: Name of the queue
            credentials: Agent credentials
            timeout: Seconds to block waiting (0 = no block)

        Returns:
            Task data or None if queue empty

        Example:
            >>> task = queues.pop("agent_tasks", creds, timeout=5)
            >>> if task:
            ...     process(task["task"])

        """
        full_queue = f"{self.PREFIX_QUEUE}{queue_name}"

        # Handle mock mode
        if self._base.use_mock:
            if full_queue not in self._mock_lists or not self._mock_lists[full_queue]:
                return None
            payload = self._mock_lists[full_queue].pop(0)
            data: dict = json.loads(payload)
            return data

        # Handle real Redis client
        if self._base._client is None:
            return None

        if timeout > 0:
            result = self._base._client.blpop(full_queue, timeout=timeout)
            if result:
                data = json.loads(result[1])
                return data
            return None

        result = self._base._client.lpop(full_queue)
        if result:
            data = json.loads(result)
            return data
        return None

    def length(self, queue_name: str) -> int:
        """Get the length of a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of items in the queue

        Example:
            >>> count = queues.length("agent_tasks")
            >>> print(f"Tasks pending: {count}")

        """
        full_queue = f"{self.PREFIX_QUEUE}{queue_name}"

        # Handle mock mode
        if self._base.use_mock:
            return len(self._mock_lists.get(full_queue, []))

        # Handle real Redis client
        if self._base._client is None:
            return 0

        return int(self._base._client.llen(full_queue))

    def peek(
        self,
        queue_name: str,
        credentials: AgentCredentials,
        count: int = 1,
    ) -> list[dict]:
        """Peek at tasks in a queue without removing them.

        Args:
            queue_name: Name of the queue
            credentials: Agent credentials
            count: Number of items to peek

        Returns:
            List of task data

        Example:
            >>> tasks = queues.peek("agent_tasks", creds, count=5)
            >>> for task in tasks:
            ...     print(task["task"]["type"])

        """
        full_queue = f"{self.PREFIX_QUEUE}{queue_name}"

        # Handle mock mode
        if self._base.use_mock:
            items = self._mock_lists.get(full_queue, [])[:count]
            return [json.loads(item) for item in items]

        # Handle real Redis client
        if self._base._client is None:
            return []

        items = self._base._client.lrange(full_queue, 0, count - 1)
        return [json.loads(item) for item in items]
