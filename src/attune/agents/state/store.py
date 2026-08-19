"""Persistent storage for agent state and execution history.

Provides file-based persistence of agent lifecycle data including
execution records, accumulated metrics, and checkpoint state for
restart recovery.

File structure:
    .attune/agents/state/
    ├── {sanitized_agent_id}.json
    └── ...

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path

from .models import AgentExecutionRecord, AgentStateRecord

logger = logging.getLogger(__name__)

# Maximum execution history entries stored per agent
MAX_HISTORY_PER_AGENT = 100

# Allowed characters in sanitized agent IDs for filenames
_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _sanitize_agent_id(agent_id: str) -> str:
    """Sanitize agent ID for use as a filename.

    Args:
        agent_id: Raw agent identifier

    Returns:
        Filesystem-safe identifier

    Raises:
        ValueError: If agent_id is empty or contains null bytes

    """
    if not agent_id:
        raise ValueError("agent_id must be a non-empty string")
    if "\x00" in agent_id:
        raise ValueError("agent_id contains null bytes")
    sanitized = _SAFE_ID_RE.sub("_", agent_id)
    # Limit length to prevent filesystem issues
    return sanitized[:200]


def _atomic_write_text(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` atomically.

    Uses ``tempfile.mkstemp`` in the same directory followed by
    ``os.replace`` so a crash mid-write or a concurrent reader never
    sees a partial file. Matches the pattern used elsewhere in the
    codebase (``spec.state._atomic_write_text``,
    ``ops.dismiss_store._write_atomic``).

    Raises:
        OSError: If the temp-write or replace fails. The temp file is
            cleaned up before re-raising.

    """
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_name, target)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError as cleanup_err:
            logger.debug(
                "Failed to unlink temp file %s after write error: %s",
                tmp_name,
                cleanup_err,
            )
        raise


class AgentStateStore:
    """Persistent storage for agent state and execution history.

    Saves agent lifecycle data to JSON files under a configurable
    directory. Integrates with PatternLearner for cross-agent learning.

    Args:
        storage_dir: Directory for state files. Defaults to
            ``.attune/agents/state`` relative to cwd.
        pattern_learner: Optional PatternLearner for cross-agent learning.

    Example:
        >>> store = AgentStateStore()
        >>> exec_id = store.record_start("sec-audit-01", "Security Auditor")
        >>> store.record_completion(
        ...     "sec-audit-01", exec_id,
        ...     success=True, findings={"issues": 0},
        ...     score=95.0, cost=0.02, execution_time_ms=1500.0,
        ... )

    """

    DEFAULT_DIR = ".attune/agents/state"

    def __init__(
        self,
        storage_dir: str | None = None,
        pattern_learner: Any | None = None,
    ) -> None:
        """Initialize the agent state store.

        Args:
            storage_dir: Directory for persisting agent state.
            pattern_learner: Optional pattern learner for insights.
        """
        self._storage_dir = Path(storage_dir or self.DEFAULT_DIR)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._pattern_learner = pattern_learner
        self._cache: dict[str, AgentStateRecord] = {}
        # Serializes read-modify-write cycles across threads. The atomic
        # replace in _atomic_write_text prevents torn files, but without
        # this lock two concurrent mutators on the same record would
        # load the same snapshot and the second save would drop the
        # first's update. Cross-process writers remain last-writer-wins
        # (never corrupted, thanks to os.replace).
        self._lock = threading.Lock()

    def record_start(
        self,
        agent_id: str,
        role: str,
        input_summary: str = "",
    ) -> str:
        """Record the start of an agent execution.

        Args:
            agent_id: Unique agent identifier
            role: Human-readable agent role
            input_summary: Brief description of the input

        Returns:
            execution_id for use in record_completion/record_failure

        """
        execution_id = uuid.uuid4().hex[:12]
        with self._lock:
            record = self._load_or_create(agent_id, role)

            execution = AgentExecutionRecord(
                execution_id=execution_id,
                agent_id=agent_id,
                role=role,
                input_summary=input_summary,
            )
            record.execution_history.append(execution)
            record.total_executions += 1
            record.last_active = datetime.now().isoformat()

            self._trim_history(record)
            self._save(record)
        return execution_id

    def record_completion(
        self,
        agent_id: str,
        execution_id: str,
        *,
        success: bool,
        findings: dict[str, Any],
        score: float,
        cost: float,
        execution_time_ms: float,
        tier_used: str = "cheap",
        confidence: float = 0.0,
    ) -> None:
        """Record the successful or failed completion of an execution.

        Args:
            agent_id: Unique agent identifier
            execution_id: ID returned by record_start
            success: Whether the execution succeeded
            findings: Structured findings dict
            score: Numeric score
            cost: LLM API cost in USD
            execution_time_ms: Wall-clock time in milliseconds
            tier_used: Final model tier used
            confidence: Confidence in result (0.0-1.0)

        """
        with self._lock:
            record = self._load_or_create(agent_id, "")
            execution = self._find_execution(record, execution_id)
            if execution is None:
                logger.warning("Execution %s not found for agent %s", execution_id, agent_id)
                return

            execution.completed_at = datetime.now().isoformat()
            execution.status = "completed" if success else "failed"
            execution.tier_used = tier_used
            execution.findings = findings
            execution.score = score
            execution.confidence = confidence
            execution.cost = cost
            execution.execution_time_ms = execution_time_ms

            if success:
                record.successful_executions += 1
            else:
                record.failed_executions += 1

            record.total_cost += cost
            record.last_active = datetime.now().isoformat()

            self._save(record)
        self._contribute_to_learner(record, execution)

    def record_failure(
        self,
        agent_id: str,
        execution_id: str,
        error: str,
    ) -> None:
        """Record a failed execution with error details.

        Args:
            agent_id: Unique agent identifier
            execution_id: ID returned by record_start
            error: Error message or traceback summary

        """
        with self._lock:
            record = self._load_or_create(agent_id, "")
            execution = self._find_execution(record, execution_id)
            if execution is None:
                logger.warning("Execution %s not found for agent %s", execution_id, agent_id)
                return

            execution.completed_at = datetime.now().isoformat()
            execution.status = "failed"
            execution.error = error

            record.failed_executions += 1
            record.last_active = datetime.now().isoformat()

            self._save(record)

    def save_checkpoint(
        self,
        agent_id: str,
        checkpoint_data: dict[str, Any],
    ) -> None:
        """Save checkpoint data for restart recovery.

        Args:
            agent_id: Unique agent identifier
            checkpoint_data: Arbitrary state dict to persist

        """
        with self._lock:
            record = self._load_or_create(agent_id, "")
            record.last_checkpoint = checkpoint_data
            record.last_active = datetime.now().isoformat()
            self._save(record)

    def get_last_checkpoint(self, agent_id: str) -> dict[str, Any] | None:
        """Get the last saved checkpoint for an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            Checkpoint dict or None if no checkpoint exists

        """
        record = self._load(agent_id)
        if record is None:
            return None
        return record.last_checkpoint or None

    def get_agent_state(self, agent_id: str) -> AgentStateRecord | None:
        """Get the full persistent state for an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            AgentStateRecord or None if agent not found

        """
        return self._load(agent_id)

    def get_all_agents(self) -> list[AgentStateRecord]:
        """Get state records for all known agents.

        Returns:
            List of AgentStateRecord sorted by last_active (newest first)

        """
        records = []
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                records.append(AgentStateRecord.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to load agent state from %s: %s", path, e)
        records.sort(key=lambda r: r.last_active or "", reverse=True)
        return records

    def search_history(
        self,
        role: str | None = None,
        min_success_rate: float = 0.0,
        limit: int = 20,
    ) -> list[AgentStateRecord]:
        """Search agent history by role and performance.

        Args:
            role: Filter by agent role (case-insensitive substring match)
            min_success_rate: Minimum success rate (0.0-1.0)
            limit: Maximum number of results

        Returns:
            Matching AgentStateRecord list

        """
        all_agents = self.get_all_agents()
        results = []
        for record in all_agents:
            if role and role.lower() not in record.role.lower():
                continue
            if record.success_rate < min_success_rate:
                continue
            results.append(record)
            if len(results) >= limit:
                break
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_or_create(self, agent_id: str, role: str) -> AgentStateRecord:
        """Load existing record or create new one."""
        record = self._load(agent_id)
        if record is None:
            record = AgentStateRecord(agent_id=agent_id, role=role)
        elif role and not record.role:
            record.role = role
        return record

    def _load(self, agent_id: str) -> AgentStateRecord | None:
        """Load agent state from disk or cache."""
        if agent_id in self._cache:
            return self._cache[agent_id]

        safe_id = _sanitize_agent_id(agent_id)
        file_path = self._storage_dir / f"{safe_id}.json"
        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            record = AgentStateRecord.from_dict(data)
            self._cache[agent_id] = record
            return record
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load state for %s: %s", agent_id, e)
            return None

    def _save(self, record: AgentStateRecord) -> Path:
        """Save agent state to disk with path validation."""
        safe_id = _sanitize_agent_id(record.agent_id)
        file_path = str(self._storage_dir / f"{safe_id}.json")
        validated_path = _validate_file_path(file_path, allowed_dir=str(self._storage_dir))

        validated_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(validated_path, json.dumps(record.to_dict(), indent=2))

        self._cache[record.agent_id] = record
        return validated_path

    def _trim_history(self, record: AgentStateRecord) -> None:
        """Trim execution history to MAX_HISTORY_PER_AGENT entries."""
        if len(record.execution_history) > MAX_HISTORY_PER_AGENT:
            record.execution_history = record.execution_history[-MAX_HISTORY_PER_AGENT:]

    def _find_execution(
        self,
        record: AgentStateRecord,
        execution_id: str,
    ) -> AgentExecutionRecord | None:
        """Find an execution record by ID."""
        for execution in reversed(record.execution_history):
            if execution.execution_id == execution_id:
                return execution
        return None

    def _contribute_to_learner(
        self,
        record: AgentStateRecord,
        execution: AgentExecutionRecord,
    ) -> None:
        """Contribute execution data to PatternLearner if available."""
        if self._pattern_learner is None:
            return
        try:
            self._pattern_learner.record(
                pattern=record.role,
                success=execution.status == "completed",
                duration_seconds=execution.execution_time_ms / 1000.0,
                cost=execution.cost,
                confidence=execution.confidence,
                context_features={
                    "agent_id": record.agent_id,
                    "tier_used": execution.tier_used,
                },
            )
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Pattern learning is optional; don't fail agent operations
            logger.warning("Failed to contribute to pattern learner: %s", e)
