"""Metrics Collection and Persistence.

Collects and persists Attune AI metrics in SQLite.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import sqlite3


class MetricsCollector:
    """Collect and persist Attune AI metrics

    Tracks:
    - Success rates
    - Average response times
    - Trust trajectory trends
    """

    def __init__(self, db_path: str = "./metrics.db"):
        """Initialize MetricsCollector with a SQLite database.

        Args:
            db_path: Path to the SQLite database file.

        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize SQLite database for metrics."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time_ms REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """,
            )

            self._migrate_legacy_level_column(conn)

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user
                ON metrics(user_id)
            """,
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON metrics(timestamp)
            """,
            )

            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _migrate_legacy_level_column(conn: sqlite3.Connection) -> None:
        """Drop the pre-15.0.0 ``empathy_level`` column if present.

        Databases created before 15.0.0 have a NOT NULL
        ``empathy_level`` column that would reject the new
        level-free inserts.
        """
        cursor = conn.cursor()
        columns = [row[1] for row in cursor.execute("PRAGMA table_info(metrics)")]
        if "empathy_level" not in columns:
            return

        cursor.execute("DROP INDEX IF EXISTS idx_user_level")
        try:
            cursor.execute("ALTER TABLE metrics DROP COLUMN empathy_level")
            return
        except sqlite3.OperationalError:
            pass  # SQLite < 3.35 has no DROP COLUMN — rebuild below.

        # DDL runs in autocommit under the driver's implicit transaction, so
        # an interrupted rebuild would leave an orphan metrics_new behind and
        # every later retry would die on "table metrics_new already exists".
        # SQLite's DDL *is* transactional, so an explicit transaction makes
        # the whole rebuild atomic; the leading DROP clears any orphan left
        # by a pre-fix build.
        previous_isolation = conn.isolation_level
        conn.isolation_level = None
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("DROP TABLE IF EXISTS metrics_new")
        cursor.execute(
            """
            CREATE TABLE metrics_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                response_time_ms REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """,
        )
        cursor.execute(
            """
            INSERT INTO metrics_new (
                id, user_id, success, response_time_ms, timestamp, metadata
            )
            SELECT id, user_id, success, response_time_ms, timestamp, metadata
            FROM metrics
        """,
        )
        cursor.execute("DROP TABLE metrics")
        cursor.execute("ALTER TABLE metrics_new RENAME TO metrics")
        cursor.execute("COMMIT")
        conn.isolation_level = previous_isolation

    def record_metric(
        self,
        user_id: str,
        success: bool,
        response_time_ms: float,
        metadata: dict | None = None,
    ) -> None:
        """Record a single metric event.

        Args:
            user_id: User identifier
            success: Whether the operation succeeded
            response_time_ms: Response time in milliseconds
            metadata: Optional additional data

        Example:
            >>> collector = MetricsCollector()
            >>> collector.record_metric(
            ...     user_id="user123",
            ...     success=True,
            ...     response_time_ms=250.5,
            ...     metadata={"bottlenecks_predicted": 3}
            ... )

        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO metrics (
                user_id, success, response_time_ms, metadata
            ) VALUES (?, ?, ?, ?)
        """,
            (
                user_id,
                success,
                response_time_ms,
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        conn.close()

    def get_user_stats(self, user_id: str) -> dict:
        """Get aggregated statistics for a user

        Args:
            user_id: User identifier

        Returns:
            Dict with statistics

        Example:
            >>> collector = MetricsCollector()
            >>> stats = collector.get_user_stats("user123")
            >>> print(f"Success rate: {stats['success_rate']:.1%}")

        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) as total_operations,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                AVG(response_time_ms) as avg_response_time,
                MIN(timestamp) as first_use,
                MAX(timestamp) as last_use
            FROM metrics
            WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()

        if not row or row["total_operations"] == 0:
            conn.close()
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_response_time_ms": 0.0,
                "first_use": None,
                "last_use": None,
            }

        conn.close()

        return {
            "total_operations": row["total_operations"],
            "success_rate": row["successes"] / row["total_operations"],
            "avg_response_time_ms": row["avg_response_time"],
            "first_use": row["first_use"],
            "last_use": row["last_use"],
        }
