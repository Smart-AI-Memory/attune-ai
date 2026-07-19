"""Telemetry storage implementation.

File-based storage for telemetry records.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
import os
from collections import deque
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeVar

from attune.security.path_validation import _validate_file_path

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

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Size guard for the canonical run stream (run-record-corpus RC-5):
# past this, history rotates into ``<dir>/archive/`` — never deleted,
# so the pipeline-learner corpus keeps its full span.
_RUNS_ROTATE_BYTES = 50 * 1024 * 1024


def _canonical_runs_file() -> Path:
    """Canonical home-global run-record stream (run-record-corpus RC-1).

    Resolved under ``ATTUNE_HOME`` (env override -> ``~/.attune``), the
    same mechanism ``UsageTracker`` uses, so run records from every
    checkout and worktree consolidate into ONE stream — and the test
    suite's ``ATTUNE_HOME`` isolation fixture redirects them off the
    real corpus automatically.
    """
    home = os.environ.get("ATTUNE_HOME")
    attune_dir = Path(home).expanduser() if home else Path.home() / ".attune"
    return attune_dir / "telemetry" / "workflow_runs.jsonl"


class TelemetryStore:
    """JSONL file-based telemetry backend (default implementation).

    Stores records in JSONL format for easy streaming and analysis.
    Implements the TelemetryBackend protocol.

    Supports both core telemetry and Tier 1 automation monitoring.
    """

    def __init__(self, storage_dir: str | None = None):
        """Initialize telemetry store.

        Args:
            storage_dir: Directory for telemetry files. ``None`` (the
                production default) keeps project-scoped files under the
                cwd-relative ``.attune`` but routes workflow RUN records
                to the canonical home-global stream
                ``<ATTUNE_HOME|~/.attune>/telemetry/workflow_runs.jsonl``
                (docs/specs/run-record-corpus/ RC-1). Passing an explicit
                directory keeps EVERY file under it.

        Raises:
            ValueError: If storage_dir is invalid or targets a system directory
                (prevents CWE-22 arbitrary-write via a caller-supplied path).

        """
        explicit = storage_dir is not None
        # Validate before any filesystem op — storage_dir may come from a CLI
        # arg (`--storage-dir`) or other caller-controlled input.
        self.storage_dir = _validate_file_path(str(storage_dir if explicit else ".attune"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Core telemetry files
        self.calls_file = self.storage_dir / "llm_calls.jsonl"
        self.workflows_file = (
            self.storage_dir / "workflow_runs.jsonl" if explicit else _canonical_runs_file()
        )

        # Tier 1 automation monitoring files
        self.task_routing_file = self.storage_dir / "task_routing.jsonl"
        self.test_executions_file = self.storage_dir / "test_executions.jsonl"
        self.coverage_history_file = self.storage_dir / "coverage_history.jsonl"
        self.agent_assignments_file = self.storage_dir / "agent_assignments.jsonl"

        # Per-file test tracking
        self.file_tests_file = self.storage_dir / "file_tests.jsonl"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _append_record(self, file: Path, record: Any) -> None:
        """Append a single record to a JSONL file."""
        with file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def _read_jsonl(
        self,
        file: Path,
        record_cls: type[T],
        *,
        since: datetime | None = None,
        timestamp_field: str = "timestamp",
        limit: int = 1000,
        extra_filter: Callable[[T], bool] | None = None,
    ) -> list[T]:
        """Read and filter records from a JSONL file.

        Args:
            file: Path to the JSONL file
            record_cls: Record class with a from_dict() classmethod
            since: Only return records after this time
            timestamp_field: Name of the timestamp attribute on the record
            limit: Maximum records to return (the MOST RECENT ``limit``)
            extra_filter: Optional predicate — return True to include

        Returns:
            The most recent ``limit`` matching records, oldest-first.

        """
        if not file.exists():
            return []

        # JSONL is appended chronologically (oldest first). A top-down read
        # with an early ``break`` at ``limit`` returned the OLDEST matches —
        # wrong for the "recent" contract callers rely on (e.g. records[-1]
        # is meant to be the latest). A bounded deque keeps the last ``limit``
        # matching records in O(limit) memory in a single pass.
        records: deque[T] = deque(maxlen=limit)
        with file.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = record_cls.from_dict(data)

                    if since:
                        ts = getattr(record, timestamp_field, "")
                        if _parse_timestamp(ts) < since:
                            continue

                    if extra_filter and not extra_filter(record):
                        continue

                    records.append(record)
                except (json.JSONDecodeError, KeyError):
                    logger.debug("Skipping malformed record in %s", file.name)
                    continue

        return list(records)

    # ------------------------------------------------------------------
    # Log methods
    # ------------------------------------------------------------------

    def log_call(self, record: LLMCallRecord) -> None:
        """Log an LLM call record."""
        self._append_record(self.calls_file, record)

    def log_workflow(self, record: WorkflowRunRecord) -> None:
        """Log a workflow run record to the canonical stream (size-rotated)."""
        try:
            self.workflows_file.parent.mkdir(parents=True, exist_ok=True)
            self._rotate_runs_file_if_needed()
        except OSError as exc:
            logger.warning("telemetry: run-stream prep failed: %s", exc)
        self._append_record(self.workflows_file, record)

    def _rotate_runs_file_if_needed(self) -> None:
        """Rotate the run stream past ``_RUNS_ROTATE_BYTES`` (RC-5).

        History moves to ``<dir>/archive/workflow_runs-<utc>.jsonl`` so
        the miner keeps its full span; the live file stays bounded.
        Never deletes.
        """
        try:
            if (
                not self.workflows_file.is_file()
                or self.workflows_file.stat().st_size < _RUNS_ROTATE_BYTES
            ):
                return
            archive_dir = self.workflows_file.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            dest = archive_dir / f"workflow_runs-{stamp}.jsonl"
            suffix = 0
            while dest.exists():
                suffix += 1
                dest = archive_dir / f"workflow_runs-{stamp}-{suffix}.jsonl"
            self.workflows_file.rename(dest)
        except OSError as exc:
            logger.warning("telemetry: run-stream rotation failed: %s", exc)

    def log_task_routing(self, record: TaskRoutingRecord) -> None:
        """Log a task routing decision."""
        self._append_record(self.task_routing_file, record)

    def log_test_execution(self, record: TestExecutionRecord) -> None:
        """Log a test execution."""
        self._append_record(self.test_executions_file, record)

    def log_coverage(self, record: CoverageRecord) -> None:
        """Log coverage metrics."""
        self._append_record(self.coverage_history_file, record)

    def log_agent_assignment(self, record: AgentAssignmentRecord) -> None:
        """Log an agent assignment."""
        self._append_record(self.agent_assignments_file, record)

    def log_file_test(self, record: FileTestRecord) -> None:
        """Log a per-file test execution record."""
        self._append_record(self.file_tests_file, record)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

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
        return self._read_jsonl(
            self.calls_file,
            LLMCallRecord,
            since=since,
            limit=limit,
            extra_filter=((lambda r: r.workflow_name == workflow_name) if workflow_name else None),
        )

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
        return self._read_jsonl(
            self.workflows_file,
            WorkflowRunRecord,
            since=since,
            timestamp_field="started_at",
            limit=limit,
            extra_filter=((lambda r: r.workflow_name == workflow_name) if workflow_name else None),
        )

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
        return self._read_jsonl(
            self.task_routing_file,
            TaskRoutingRecord,
            since=since,
            limit=limit,
            extra_filter=((lambda r: r.status == status) if status else None),
        )

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
        return self._read_jsonl(
            self.test_executions_file,
            TestExecutionRecord,
            since=since,
            limit=limit,
            extra_filter=(lambda r: r.success) if success_only else None,
        )

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
        return self._read_jsonl(
            self.coverage_history_file,
            CoverageRecord,
            since=since,
            limit=limit,
        )

    def get_agent_assignments(
        self,
        since: datetime | None = None,
        automated_only: bool = True,
        limit: int = 1000,
    ) -> list[AgentAssignmentRecord]:
        """Get agent assignment records.

        Args:
            since: Only return records after this time
            automated_only: Only return Tier 1 automation eligible
            limit: Maximum records to return

        Returns:
            List of AgentAssignmentRecord

        """
        return self._read_jsonl(
            self.agent_assignments_file,
            AgentAssignmentRecord,
            since=since,
            limit=limit,
            extra_filter=((lambda r: r.automated_eligible) if automated_only else None),
        )

    def get_file_tests(
        self,
        file_path: str | None = None,
        since: datetime | None = None,
        result_filter: str | None = None,
        limit: int = 1000,
    ) -> list[FileTestRecord]:
        """Get per-file test records with optional filters.

        Args:
            file_path: Filter by specific file path
            since: Only return records after this time
            result_filter: Filter by result (passed, failed, error,
                skipped, no_tests)
            limit: Maximum records to return

        Returns:
            List of FileTestRecord

        """

        def _filter(r: FileTestRecord) -> bool:
            if file_path and r.file_path != file_path:
                return False
            if result_filter and r.last_test_result != result_filter:
                return False
            return True

        has_extra = file_path is not None or result_filter is not None
        return self._read_jsonl(
            self.file_tests_file,
            FileTestRecord,
            since=since,
            limit=limit,
            extra_filter=_filter if has_extra else None,
        )

    # ------------------------------------------------------------------
    # Aggregation methods
    # ------------------------------------------------------------------

    def get_summary(
        self,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated telemetry summary in a single JSONL pass.

        Streams records from JSONL files and computes totals without
        loading all records into memory. Prefers workflow records;
        falls back to LLM call records if no workflows exist.

        Args:
            since: Only include records after this time

        Returns:
            Dict with workflow_count, call_count, total_cost,
            total_tokens, source

        """
        # Try workflows first
        wf_count = 0
        total_cost = 0.0
        total_tokens = 0

        if self.workflows_file.exists():
            with open(self.workflows_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if since:
                            ts = data.get("started_at", "")
                            if _parse_timestamp(ts) < since:
                                continue
                        wf_count += 1
                        total_cost += data.get("total_cost", 0.0)
                        total_tokens += data.get("total_input_tokens", 0)
                        total_tokens += data.get("total_output_tokens", 0)
                    except (
                        json.JSONDecodeError,
                        KeyError,
                        ValueError,
                    ):
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
            with open(self.calls_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        if since:
                            ts = data.get("timestamp", "")
                            if _parse_timestamp(ts) < since:
                                continue
                        call_count += 1
                        total_cost += data.get("estimated_cost", 0.0)
                        total_tokens += data.get("input_tokens", 0)
                        total_tokens += data.get("output_tokens", 0)
                    except (
                        json.JSONDecodeError,
                        KeyError,
                        ValueError,
                    ):
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

    def get_latest_file_test(self, file_path: str) -> FileTestRecord | None:
        """Get the most recent test record for a specific file.

        Streams the JSONL file keeping only the last match,
        avoiding loading all records into memory.

        Args:
            file_path: Path to the source file

        Returns:
            Most recent FileTestRecord or None if not found

        """
        if not self.file_tests_file.exists():
            return None

        latest: FileTestRecord | None = None
        with open(self.file_tests_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    record = FileTestRecord.from_dict(data)
                    if record.file_path == file_path:
                        latest = record
                except (json.JSONDecodeError, KeyError):
                    continue
        return latest

    def get_files_needing_tests(
        self,
        stale_only: bool = False,
        failed_only: bool = False,
    ) -> list[FileTestRecord]:
        """Get files that need test attention.

        Streams the JSONL file and keeps only the latest record
        per file path, then filters by the requested criteria.

        Args:
            stale_only: Only return files with stale tests
            failed_only: Only return files with failed tests

        Returns:
            List of FileTestRecord for files needing attention

        """
        # Stream file, keeping only latest record per path
        latest_by_file: dict[str, FileTestRecord] = {}
        if self.file_tests_file.exists():
            with open(self.file_tests_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        record = FileTestRecord.from_dict(data)
                        existing = latest_by_file.get(record.file_path)
                        if existing is None or record.timestamp > existing.timestamp:
                            latest_by_file[record.file_path] = record
                    except (json.JSONDecodeError, KeyError):
                        continue

        _NEEDS_ATTENTION = ("failed", "error", "no_tests")

        def _needs_attention(record: FileTestRecord) -> bool:
            if stale_only:
                return record.is_stale
            if failed_only:
                return record.last_test_result in ("failed", "error")
            # Default: stale OR failed OR no_tests
            return record.is_stale or record.last_test_result in _NEEDS_ATTENTION

        return [r for r in latest_by_file.values() if _needs_attention(r)]
