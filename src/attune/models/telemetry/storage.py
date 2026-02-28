"""Telemetry storage implementation.

File-based storage for telemetry records.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .backend import _parse_timestamp
from .data_models import (
    AgentAssignmentRecord,
    CoverageRecord,
    FileTestRecord,
    LLMCallRecord,
    TaskRoutingRecord,
    TestExecutionRecord,
    WorkflowRunRecord,
)


class TelemetryStore:
    """JSONL file-based telemetry backend (default implementation).

    Stores records in JSONL format for easy streaming and analysis.
    Implements the TelemetryBackend protocol.

    Supports both core telemetry and Tier 1 automation monitoring.
    """

    def __init__(self, storage_dir: str = ".attune"):
        """Initialize telemetry store.

        Args:
            storage_dir: Directory for telemetry files

        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Core telemetry files
        self.calls_file = self.storage_dir / "llm_calls.jsonl"
        self.workflows_file = self.storage_dir / "workflow_runs.jsonl"

        # Tier 1 automation monitoring files
        self.task_routing_file = self.storage_dir / "task_routing.jsonl"
        self.test_executions_file = self.storage_dir / "test_executions.jsonl"
        self.coverage_history_file = self.storage_dir / "coverage_history.jsonl"
        self.agent_assignments_file = self.storage_dir / "agent_assignments.jsonl"

        # Per-file test tracking
        self.file_tests_file = self.storage_dir / "file_tests.jsonl"

    def log_call(self, record: LLMCallRecord) -> None:
        """Log an LLM call record."""
        with open(self.calls_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def log_workflow(self, record: WorkflowRunRecord) -> None:
        """Log a workflow run record."""
        with open(self.workflows_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def get_calls(
        self,
        since: datetime | None = None,
        workflow_name: str | None = None,
        limit: int = 1000,
    ) -> list[LLMCallRecord]:
        """Get LLM call records.

        Args:
            since: Only return records after this time
            workflow_name: Filter by workflow name
            limit: Maximum records to return

        Returns:
            List of LLMCallRecord

        """
        records: list[LLMCallRecord] = []
        if not self.calls_file.exists():
            return records

        with open(self.calls_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = LLMCallRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    if workflow_name and record.workflow_name != workflow_name:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_workflows(
        self,
        since: datetime | None = None,
        workflow_name: str | None = None,
        limit: int = 100,
    ) -> list[WorkflowRunRecord]:
        """Get workflow run records.

        Args:
            since: Only return records after this time
            workflow_name: Filter by workflow name
            limit: Maximum records to return

        Returns:
            List of WorkflowRunRecord

        """
        records: list[WorkflowRunRecord] = []
        if not self.workflows_file.exists():
            return records

        with open(self.workflows_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = WorkflowRunRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.started_at)
                        if record_time < since:
                            continue

                    if workflow_name and record.workflow_name != workflow_name:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_summary(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated telemetry summary in a single JSONL pass.

        Streams records from JSONL files and computes totals without loading
        all records into memory. Prefers workflow records; falls back to
        LLM call records if no workflows exist.

        Args:
            since: Only include records after this time

        Returns:
            Dict with workflow_count, call_count, total_cost, total_tokens, source

        """
        # Try workflows first
        wf_count = 0
        total_cost = 0.0
        total_tokens = 0

        if self.workflows_file.exists():
            with open(self.workflows_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if since:
                            record_time = _parse_timestamp(data.get("started_at", ""))
                            if record_time < since:
                                continue
                        wf_count += 1
                        total_cost += data.get("total_cost", 0.0)
                        total_tokens += data.get("total_input_tokens", 0)
                        total_tokens += data.get("total_output_tokens", 0)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        if wf_count > 0:
            return {
                "workflow_count": wf_count,
                "call_count": 0,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "source": "workflows",
            }

        # Fall back to LLM calls
        call_count = 0
        total_cost = 0.0
        total_tokens = 0

        if self.calls_file.exists():
            with open(self.calls_file) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if since:
                            record_time = _parse_timestamp(data.get("timestamp", ""))
                            if record_time < since:
                                continue
                        call_count += 1
                        total_cost += data.get("estimated_cost", 0.0)
                        total_tokens += data.get("input_tokens", 0)
                        total_tokens += data.get("output_tokens", 0)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

        if call_count > 0:
            return {
                "workflow_count": 0,
                "call_count": call_count,
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "source": "calls",
            }

        return {
            "workflow_count": 0,
            "call_count": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "source": "none",
        }

    # Tier 1 automation monitoring methods

    def log_task_routing(self, record: TaskRoutingRecord) -> None:
        """Log a task routing decision."""
        with open(self.task_routing_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def log_test_execution(self, record: TestExecutionRecord) -> None:
        """Log a test execution."""
        with open(self.test_executions_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def log_coverage(self, record: CoverageRecord) -> None:
        """Log coverage metrics."""
        with open(self.coverage_history_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def log_agent_assignment(self, record: AgentAssignmentRecord) -> None:
        """Log an agent assignment."""
        with open(self.agent_assignments_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def get_task_routings(
        self,
        since: datetime | None = None,
        status: str | None = None,
        limit: int = 1000,
    ) -> list[TaskRoutingRecord]:
        """Get task routing records.

        Args:
            since: Only return records after this time
            status: Filter by status (pending, running, completed, failed)
            limit: Maximum records to return

        Returns:
            List of TaskRoutingRecord

        """
        records: list[TaskRoutingRecord] = []
        if not self.task_routing_file.exists():
            return records

        with open(self.task_routing_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = TaskRoutingRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    if status and record.status != status:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_test_executions(
        self,
        since: datetime | None = None,
        success_only: bool = False,
        limit: int = 100,
    ) -> list[TestExecutionRecord]:
        """Get test execution records.

        Args:
            since: Only return records after this time
            success_only: Only return successful test runs
            limit: Maximum records to return

        Returns:
            List of TestExecutionRecord

        """
        records: list[TestExecutionRecord] = []
        if not self.test_executions_file.exists():
            return records

        with open(self.test_executions_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = TestExecutionRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    if success_only and not record.success:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_coverage_history(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CoverageRecord]:
        """Get coverage history records.

        Args:
            since: Only return records after this time
            limit: Maximum records to return

        Returns:
            List of CoverageRecord

        """
        records: list[CoverageRecord] = []
        if not self.coverage_history_file.exists():
            return records

        with open(self.coverage_history_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = CoverageRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_agent_assignments(
        self,
        since: datetime | None = None,
        automated_only: bool = True,
        limit: int = 1000,
    ) -> list[AgentAssignmentRecord]:
        """Get agent assignment records.

        Args:
            since: Only return records after this time
            automated_only: Only return assignments eligible for Tier 1 automation
            limit: Maximum records to return

        Returns:
            List of AgentAssignmentRecord

        """
        records: list[AgentAssignmentRecord] = []
        if not self.agent_assignments_file.exists():
            return records

        with open(self.agent_assignments_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = AgentAssignmentRecord.from_dict(data)

                    # Apply filters
                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    if automated_only and not record.automated_eligible:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    # Per-file test tracking methods

    def log_file_test(self, record: "FileTestRecord") -> None:
        """Log a per-file test execution record.

        Args:
            record: FileTestRecord to log

        """
        with open(self.file_tests_file, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def get_file_tests(
        self,
        file_path: str | None = None,
        since: datetime | None = None,
        result_filter: str | None = None,
        limit: int = 1000,
    ) -> list["FileTestRecord"]:
        """Get per-file test records with optional filters.

        Args:
            file_path: Filter by specific file path
            since: Only return records after this time
            result_filter: Filter by result (passed, failed, error, skipped, no_tests)
            limit: Maximum records to return

        Returns:
            List of FileTestRecord

        """
        records: list[FileTestRecord] = []
        if not self.file_tests_file.exists():
            return records

        with open(self.file_tests_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = FileTestRecord.from_dict(data)

                    # Apply filters
                    if file_path and record.file_path != file_path:
                        continue

                    if since:
                        record_time = _parse_timestamp(record.timestamp)
                        if record_time < since:
                            continue

                    if result_filter and record.last_test_result != result_filter:
                        continue

                    records.append(record)

                    if len(records) >= limit:
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

        return records

    def get_latest_file_test(self, file_path: str) -> "FileTestRecord | None":
        """Get the most recent test record for a specific file.

        Args:
            file_path: Path to the source file

        Returns:
            Most recent FileTestRecord or None if not found

        """
        records = self.get_file_tests(file_path=file_path, limit=10000)
        if not records:
            return None

        # Return the most recent record (last one since we read in chronological order)
        return records[-1]

    def get_files_needing_tests(
        self,
        stale_only: bool = False,
        failed_only: bool = False,
    ) -> list["FileTestRecord"]:
        """Get files that need test attention.

        Args:
            stale_only: Only return files with stale tests
            failed_only: Only return files with failed tests

        Returns:
            List of FileTestRecord for files needing attention

        """
        all_records = self.get_file_tests(limit=100000)

        # Get latest record per file
        latest_by_file: dict[str, FileTestRecord] = {}
        for record in all_records:
            existing = latest_by_file.get(record.file_path)
            if existing is None or record.timestamp > existing.timestamp:
                latest_by_file[record.file_path] = record

        # Filter based on criteria
        results = []
        for record in latest_by_file.values():
            if stale_only and not record.is_stale:
                continue
            if failed_only and record.last_test_result not in ("failed", "error"):
                continue
            if not stale_only and not failed_only:
                # Return all files needing attention (stale OR failed OR no_tests)
                if (
                    record.last_test_result not in ("failed", "error", "no_tests")
                    and not record.is_stale
                ):
                    continue
            results.append(record)

        return results
