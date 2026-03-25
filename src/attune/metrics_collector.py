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
    - Empathy level usage
    - Success rates by level
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
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                empathy_level INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                response_time_ms REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """,
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_user_level
            ON metrics(user_id, empathy_level)
        """,
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON metrics(timestamp)
        """,
        )

        conn.commit()
        conn.close()

    def record_metric(
        self,
        user_id: str,
        empathy_level: int,
        success: bool,
        response_time_ms: float,
        metadata: dict | None = None,
    ) -> None:
        """Record a single metric event.

        Args:
            user_id: User identifier
            empathy_level: 1-5 empathy level used
            success: Whether the operation succeeded
            response_time_ms: Response time in milliseconds
            metadata: Optional additional data

        Example:
            >>> collector = MetricsCollector()
            >>> collector.record_metric(
            ...     user_id="user123",
            ...     empathy_level=4,
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
                user_id, empathy_level, success, response_time_ms, metadata
            ) VALUES (?, ?, ?, ?, ?)
        """,
            (
                user_id,
                empathy_level,
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

        # Get per-level breakdown
        cursor.execute(
            """
            SELECT
                empathy_level,
                COUNT(*) as operations,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
            FROM metrics
            WHERE user_id = ?
            GROUP BY empathy_level
            ORDER BY empathy_level
        """,
            (user_id,),
        )

        level_stats = {}
        for level_row in cursor.fetchall():
            level = level_row["empathy_level"]
            ops = level_row["operations"]
            level_stats[f"level_{level}"] = {
                "operations": ops,
                "success_rate": level_row["successes"] / ops if ops > 0 else 0.0,
            }

        conn.close()

        return {
            "total_operations": row["total_operations"],
            "success_rate": row["successes"] / row["total_operations"],
            "avg_response_time_ms": row["avg_response_time"],
            "first_use": row["first_use"],
            "last_use": row["last_use"],
            "by_level": level_stats,
        }
