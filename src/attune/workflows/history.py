"""SQLite-backed workflow history storage.

Replaces JSON file-based history with structured, queryable storage.
Provides concurrent-safe workflow execution history with fast queries.

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from attune.logging_config import get_logger

if TYPE_CHECKING:
    from .base import WorkflowResult

logger = get_logger(__name__)


class WorkflowHistoryStore:
    """SQLite-backed workflow history with migrations.

    Provides concurrent-safe storage with fast queries for workflow execution history.

    Features:
        - Concurrent-safe (SQLite ACID guarantees)
        - Fast queries with indexes
        - Unlimited history (no artificial limits)
        - Flexible filtering by workflow, provider, date range
        - Analytics-ready with aggregate queries

    Example:
        >>> store = WorkflowHistoryStore()
        >>> store.record_run("run-123", "test-gen", "anthropic", result)
        >>> stats = store.get_stats()
        >>> recent = store.query_runs(limit=10)
        >>> store.close()
    """

    SCHEMA_VERSION = 1
    DEFAULT_DB = ".attune/history.db"

    def __init__(self, db_path: str = DEFAULT_DB):
        """Initialize history store.

        Args:
            db_path: Path to SQLite database file (default: .attune/history.db)
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Enable thread-safe access
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._migrate()

    def _migrate(self) -> None:
        """Create schema if needed.

        Creates workflow_runs and workflow_stages tables with appropriate indexes.
        Idempotent - safe to call multiple times.
        """
        # Main workflow runs table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                provider TEXT NOT NULL,
                success INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                baseline_cost REAL NOT NULL,
                savings REAL NOT NULL,
                savings_percent REAL NOT NULL,
                error TEXT,
                error_type TEXT,
                transient INTEGER DEFAULT 0,
                xml_parsed INTEGER DEFAULT 0,
                summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Workflow stages (1:many relationship)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_stages (
                stage_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                stage_name TEXT NOT NULL,
                tier TEXT NOT NULL,
                skipped INTEGER NOT NULL DEFAULT 0,
                skip_reason TEXT,
                cost REAL NOT NULL DEFAULT 0.0,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                FOREIGN KEY (run_id) REFERENCES workflow_runs(run_id)
            )
        """
        )

        # Indexes for common queries
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_workflow_name
            ON workflow_runs(workflow_name)
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_started_at
            ON workflow_runs(started_at DESC)
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_provider
            ON workflow_runs(provider)
        """
        )

        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_success
            ON workflow_runs(success)
        """
        )

        # Index for stage queries
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_run_stages
            ON workflow_stages(run_id)
        """
        )

        self.conn.commit()
        logger.debug(f"History store initialized: {self.db_path}")

    def record_run(
        self,
        run_id: str,
        workflow_name: str,
        provider: str,
        result: WorkflowResult,
    ) -> None:
        """Record a workflow execution.

        Args:
            run_id: Unique identifier for this run
            workflow_name: Name of the workflow
            provider: Provider used (anthropic, openai, google)
            result: WorkflowResult object with execution details

        Raises:
            sqlite3.IntegrityError: If run_id already exists
            sqlite3.OperationalError: If database is locked
        """
        cursor = self.conn.cursor()

        try:
            # Insert run record
            cursor.execute(
                """
                INSERT INTO workflow_runs (
                    run_id, workflow_name, provider, success,
                    started_at, completed_at, duration_ms,
                    total_cost, baseline_cost, savings, savings_percent,
                    error, error_type, transient,
                    xml_parsed, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    run_id,
                    workflow_name,
                    provider,
                    1 if result.success else 0,
                    result.started_at.isoformat(),
                    result.completed_at.isoformat(),
                    result.total_duration_ms,
                    result.cost_report.total_cost,
                    result.cost_report.baseline_cost,
                    result.cost_report.savings,
                    result.cost_report.savings_percent,
                    result.error,
                    result.error_type,
                    1 if result.transient else 0,
                    (
                        1
                        if isinstance(result.final_output, dict)
                        and result.final_output.get("xml_parsed")
                        else 0
                    ),
                    (
                        str(result.final_output.get("summary"))
                        if isinstance(result.final_output, dict)
                        and result.final_output.get("summary") is not None
                        else None
                    ),
                ),
            )

            # Insert stage records
            for stage in result.stages:
                cursor.execute(
                    """
                    INSERT INTO workflow_stages (
                        run_id, stage_name, tier, skipped, skip_reason,
                        cost, duration_ms, input_tokens, output_tokens
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        run_id,
                        stage.name,
                        stage.tier.value,
                        1 if stage.skipped else 0,
                        stage.skip_reason,
                        stage.cost,
                        stage.duration_ms,
                        stage.input_tokens,
                        stage.output_tokens,
                    ),
                )

            self.conn.commit()
            logger.debug(f"Recorded workflow run: {run_id} ({workflow_name})")

        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            logger.warning(f"Run ID already exists: {run_id}")
            raise ValueError(f"Duplicate run_id: {run_id}") from e
        except sqlite3.OperationalError as e:
            self.conn.rollback()
            logger.error(f"Database error recording run: {e}")
            raise

    def query_runs(
        self,
        workflow_name: str | None = None,
        provider: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        success_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        """Query workflow runs with flexible filters.

        Args:
            workflow_name: Filter by workflow name (optional)
            provider: Filter by provider (optional)
            since: Filter runs after this datetime (optional)
            until: Filter runs before this datetime (optional)
            success_only: Only return successful runs (default: False)
            limit: Maximum number of runs to return (default: 100)

        Returns:
            List of workflow run dictionaries with stages included

        Example:
            >>> # Get recent successful test-gen runs
            >>> runs = store.query_runs(
            ...     workflow_name="test-gen",
            ...     success_only=True,
            ...     limit=10
            ... )
        """
        query = "SELECT * FROM workflow_runs WHERE 1=1"
        params: list[Any] = []

        if workflow_name:
            query += " AND workflow_name = ?"
            params.append(workflow_name)

        if provider:
            query += " AND provider = ?"
            params.append(provider)

        if since:
            query += " AND started_at >= ?"
            params.append(since.isoformat())

        if until:
            query += " AND started_at <= ?"
            params.append(until.isoformat())

        if success_only:
            query += " AND success = 1"

        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        runs = []
        for row in cursor.fetchall():
            run = dict(row)

            # Fetch stages for this run
            cursor.execute(
                """
                SELECT * FROM workflow_stages
                WHERE run_id = ?
                ORDER BY stage_id
            """,
                (run["run_id"],),
            )

            run["stages"] = [dict(s) for s in cursor.fetchall()]
            runs.append(run)

        return runs

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics across all workflow runs.

        Returns:
            Dictionary with statistics including:
                - total_runs: Total number of runs
                - successful_runs: Number of successful runs
                - by_workflow: Stats grouped by workflow name
                - by_provider: Stats grouped by provider
                - by_tier: Total cost grouped by tier
                - recent_runs: Last 10 runs
                - total_cost: Total cost across all runs
                - total_savings: Total savings from tier optimization
                - avg_savings_percent: Average savings percentage

        Example:
            >>> stats = store.get_stats()
            >>> print(f"Total savings: ${stats['total_savings']:.2f}")
            >>> print(f"Success rate: {stats['successful_runs'] / stats['total_runs']:.1%}")
        """
        cursor = self.conn.cursor()

        # Total runs by workflow
        cursor.execute(
            """
            SELECT
                workflow_name,
                COUNT(*) as runs,
                SUM(total_cost) as cost,
                SUM(savings) as savings,
                SUM(success) as successful
            FROM workflow_runs
            GROUP BY workflow_name
        """
        )
        by_workflow = {row["workflow_name"]: dict(row) for row in cursor.fetchall()}

        # Total runs by provider
        cursor.execute(
            """
            SELECT
                provider,
                COUNT(*) as runs,
                SUM(total_cost) as cost
            FROM workflow_runs
            GROUP BY provider
        """
        )
        by_provider = {row["provider"]: dict(row) for row in cursor.fetchall()}

        # Total cost by tier
        cursor.execute(
            """
            SELECT
                tier,
                SUM(cost) as total_cost
            FROM workflow_stages
            WHERE skipped = 0
            GROUP BY tier
        """
        )
        by_tier = {row["tier"]: row["total_cost"] for row in cursor.fetchall()}

        # Recent runs (last 10)
        cursor.execute(
            """
            SELECT * FROM workflow_runs
            ORDER BY started_at DESC
            LIMIT 10
        """
        )
        recent_runs = [dict(row) for row in cursor.fetchall()]

        # Totals
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_runs,
                SUM(success) as successful_runs,
                SUM(total_cost) as total_cost,
                SUM(savings) as total_savings,
                AVG(CASE WHEN success = 1 THEN savings_percent ELSE NULL END) as avg_savings_percent
            FROM workflow_runs
        """
        )
        totals = dict(cursor.fetchone())

        return {
            "total_runs": totals["total_runs"] or 0,
            "successful_runs": totals["successful_runs"] or 0,
            "by_workflow": by_workflow,
            "by_provider": by_provider,
            "by_tier": by_tier,
            "recent_runs": recent_runs,
            "total_cost": totals["total_cost"] or 0.0,
            "total_savings": totals["total_savings"] or 0.0,
            "avg_savings_percent": totals["avg_savings_percent"] or 0.0,
        }

    def get_run_by_id(self, run_id: str) -> dict | None:
        """Get a specific run by ID.

        Args:
            run_id: The run ID to fetch

        Returns:
            Run dictionary with stages, or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,))

        row = cursor.fetchone()
        if not row:
            return None

        run = dict(row)

        # Fetch stages
        cursor.execute(
            """
            SELECT * FROM workflow_stages
            WHERE run_id = ?
            ORDER BY stage_id
        """,
            (run_id,),
        )
        run["stages"] = [dict(s) for s in cursor.fetchall()]

        return run

    def delete_run(self, run_id: str) -> bool:
        """Delete a workflow run and its stages.

        Args:
            run_id: The run ID to delete

        Returns:
            True if run was deleted, False if not found
        """
        cursor = self.conn.cursor()

        # Delete stages first (foreign key)
        cursor.execute("DELETE FROM workflow_stages WHERE run_id = ?", (run_id,))

        # Delete run
        cursor.execute("DELETE FROM workflow_runs WHERE run_id = ?", (run_id,))

        deleted = cursor.rowcount > 0
        self.conn.commit()

        if deleted:
            logger.debug(f"Deleted workflow run: {run_id}")

        return deleted

    def cleanup_old_runs(self, keep_days: int = 90) -> int:
        """Delete runs older than specified days.

        Args:
            keep_days: Number of days to keep (default: 90)

        Returns:
            Number of runs deleted
        """
        cursor = self.conn.cursor()

        # Get run IDs to delete
        cursor.execute(
            """
            SELECT run_id FROM workflow_runs
            WHERE started_at < datetime('now', '-' || ? || ' days')
        """,
            (keep_days,),
        )

        run_ids = [row["run_id"] for row in cursor.fetchall()]

        if not run_ids:
            return 0

        # Delete stages for these runs
        # Security Note: f-string builds placeholder list only ("?, ?, ?")
        # Actual data (run_ids) passed as parameters - SQL injection safe
        placeholders = ",".join("?" * len(run_ids))
        cursor.execute(
            f"DELETE FROM workflow_stages WHERE run_id IN ({placeholders})",  # nosec B608
            run_ids,
        )

        # Delete runs (same safe parameterization pattern)
        cursor.execute(
            f"DELETE FROM workflow_runs WHERE run_id IN ({placeholders})",  # nosec B608
            run_ids,
        )

        self.conn.commit()
        logger.info(f"Cleaned up {len(run_ids)} runs older than {keep_days} days")

        return len(run_ids)

    def close(self) -> None:
        """Close database connection.

        Should be called when done with the store.
        """
        self.conn.close()
        logger.debug("History store closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.close()
