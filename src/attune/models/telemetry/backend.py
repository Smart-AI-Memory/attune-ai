"""Telemetry backend interface.

Abstract base class for telemetry storage backends.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timezone
from typing import Protocol

from .data_models import (
    AgentAssignmentRecord,
    CoverageRecord,
    FileTestRecord,
    LLMCallRecord,
    TaskRoutingRecord,
    TestExecutionRecord,
    WorkflowRunRecord,
)


def _parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO format timestamp, handling 'Z' suffix for Python 3.10 compatibility.

    Args:
        timestamp_str: ISO format timestamp string, possibly with 'Z' suffix

    Returns:
        Parsed datetime object (timezone-aware UTC)

    """
    # Python 3.10's fromisoformat() doesn't handle 'Z' suffix
    timestamp_str = timestamp_str.replace("Z", "+00:00")

    dt = datetime.fromisoformat(timestamp_str)

    # Ensure timezone-aware (assume UTC for naive timestamps)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


class TelemetryBackend(Protocol):
    """Protocol for telemetry storage backends.

    Implementations can store telemetry data in different backends:
    - JSONL files (default, via TelemetryStore)
    - Database (PostgreSQL, SQLite, etc.)
    - Cloud services (DataDog, New Relic, etc.)
    - Custom backends

    Supports both core telemetry (LLM calls, workflows) and Tier 1
    automation monitoring (task routing, tests, coverage, assignments).

    Example implementing a custom backend:
        >>> class DatabaseBackend:
        ...     def log_call(self, record: LLMCallRecord) -> None:
        ...         # Insert into database
        ...         pass
        ...
        ...     def log_workflow(self, record: WorkflowRunRecord) -> None:
        ...         # Insert into database
        ...         pass
        ...
        ...     def get_calls(self, since=None, workflow_name=None, limit=1000):
        ...         # Query database
        ...         return []
        ...
        ...     def get_workflows(self, since=None, workflow_name=None, limit=100):
        ...         # Query database
        ...         return []
    """

    def log_call(self, record: LLMCallRecord) -> None:
        """Log an LLM call record."""
        ...

    def log_workflow(self, record: WorkflowRunRecord) -> None:
        """Log a workflow run record."""
        ...

    def get_calls(
        self,
        since: datetime | None = None,
        workflow_name: str | None = None,
        limit: int = 1000,
    ) -> list[LLMCallRecord]:
        """Get LLM call records with optional filters."""
        ...

    def get_workflows(
        self,
        since: datetime | None = None,
        workflow_name: str | None = None,
        limit: int = 100,
    ) -> list[WorkflowRunRecord]:
        """Get workflow run records with optional filters."""
        ...

    # Tier 1 automation monitoring methods
    def log_task_routing(self, record: TaskRoutingRecord) -> None:
        """Log a task routing decision."""
        ...

    def log_test_execution(self, record: TestExecutionRecord) -> None:
        """Log a test execution."""
        ...

    def log_coverage(self, record: CoverageRecord) -> None:
        """Log coverage metrics."""
        ...

    def log_agent_assignment(self, record: AgentAssignmentRecord) -> None:
        """Log an agent assignment."""
        ...

    def get_task_routings(
        self,
        since: datetime | None = None,
        status: str | None = None,
        limit: int = 1000,
    ) -> list[TaskRoutingRecord]:
        """Get task routing records with optional filters."""
        ...

    def get_test_executions(
        self,
        since: datetime | None = None,
        success_only: bool = False,
        limit: int = 100,
    ) -> list[TestExecutionRecord]:
        """Get test execution records with optional filters."""
        ...

    def get_coverage_history(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CoverageRecord]:
        """Get coverage history records."""
        ...

    def get_agent_assignments(
        self,
        since: datetime | None = None,
        automated_only: bool = True,
        limit: int = 1000,
    ) -> list[AgentAssignmentRecord]:
        """Get agent assignment records with optional filters."""
        ...

    # Per-file test tracking methods
    def log_file_test(self, record: "FileTestRecord") -> None:
        """Log a per-file test execution record."""
        ...

    def get_file_tests(
        self,
        file_path: str | None = None,
        since: datetime | None = None,
        result_filter: str | None = None,
        limit: int = 1000,
    ) -> list["FileTestRecord"]:
        """Get per-file test records with optional filters."""
        ...

    def get_latest_file_test(self, file_path: str) -> "FileTestRecord | None":
        """Get the most recent test record for a specific file."""
        ...
