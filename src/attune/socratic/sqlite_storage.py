"""SQLite storage backend for Socratic sessions and blueprints.

Provides SQLite-based persistence with schema management and
indexed queries for sessions, blueprints, and evaluations.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from .blueprint import WorkflowBlueprint
from .session import SessionState, SocraticSession
from .storage import StorageBackend
from .success import SuccessEvaluation

logger = logging.getLogger(__name__)


class SQLiteStorage(StorageBackend):
    """SQLite database storage for better querying.

    Example:
        >>> storage = SQLiteStorage(".attune/socratic.db")
        >>> storage.save_session(session)
        >>> sessions = storage.list_sessions(state=SessionState.COMPLETED)

    """

    def __init__(self, db_path: str = ".attune/socratic.db"):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file

        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    goal TEXT,
                    domain TEXT,
                    confidence REAL,
                    created_at TEXT,
                    updated_at TEXT,
                    data JSON NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_state ON sessions(state);
                CREATE INDEX IF NOT EXISTS idx_sessions_domain ON sessions(domain);
                CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);

                CREATE TABLE IF NOT EXISTS blueprints (
                    blueprint_id TEXT PRIMARY KEY,
                    name TEXT,
                    domain TEXT,
                    agents_count INTEGER,
                    generated_at TEXT,
                    source_session_id TEXT,
                    data JSON NOT NULL,
                    FOREIGN KEY (source_session_id) REFERENCES sessions(session_id)
                );

                CREATE INDEX IF NOT EXISTS idx_blueprints_domain ON blueprints(domain);
                CREATE INDEX IF NOT EXISTS idx_blueprints_session ON blueprints(source_session_id);

                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    blueprint_id TEXT NOT NULL,
                    overall_success INTEGER,
                    overall_score REAL,
                    evaluated_at TEXT,
                    data JSON NOT NULL,
                    FOREIGN KEY (blueprint_id) REFERENCES blueprints(blueprint_id)
                );

                CREATE INDEX IF NOT EXISTS idx_evaluations_blueprint ON evaluations(blueprint_id);
            """,
            )

    def save_session(self, session: SocraticSession) -> None:
        """Save session to database."""
        data = session.to_dict()
        domain = session.goal_analysis.domain if session.goal_analysis else None
        confidence = session.goal_analysis.confidence if session.goal_analysis else None

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions
                (session_id, state, goal, domain, confidence, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.state.value,
                    session.goal,
                    domain,
                    confidence,
                    session.created_at.isoformat(),
                    session.updated_at.isoformat(),
                    json.dumps(data, default=str),
                ),
            )

    def load_session(self, session_id: str) -> SocraticSession | None:
        """Load session from database."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

            if row:
                data = json.loads(row["data"])
                return SocraticSession.from_dict(data)
            return None

    def list_sessions(
        self,
        state: SessionState | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List sessions from database."""
        with self._get_connection() as conn:
            if state:
                rows = conn.execute(
                    """
                    SELECT session_id, state, goal, domain, confidence, created_at, updated_at
                    FROM sessions
                    WHERE state = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """,
                    (state.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT session_id, state, goal, domain, confidence, created_at, updated_at
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT ?
                """,
                    (limit,),
                ).fetchall()

            return [dict(row) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        """Delete session from database."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cursor.rowcount > 0

    def save_blueprint(self, blueprint: WorkflowBlueprint) -> None:
        """Save blueprint to database."""
        data = blueprint.to_dict()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO blueprints
                (blueprint_id, name, domain, agents_count, generated_at, source_session_id, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    blueprint.id,
                    blueprint.name,
                    blueprint.domain,
                    len(blueprint.agents),
                    blueprint.generated_at,
                    blueprint.source_session_id,
                    json.dumps(data, default=str),
                ),
            )

    def load_blueprint(self, blueprint_id: str) -> WorkflowBlueprint | None:
        """Load blueprint from database."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM blueprints WHERE blueprint_id = ?",
                (blueprint_id,),
            ).fetchone()

            if row:
                data = json.loads(row["data"])
                return WorkflowBlueprint.from_dict(data)
            return None

    def list_blueprints(
        self,
        domain: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List blueprints from database."""
        with self._get_connection() as conn:
            if domain:
                rows = conn.execute(
                    """
                    SELECT blueprint_id as id, name, domain, agents_count, generated_at
                    FROM blueprints
                    WHERE domain = ?
                    ORDER BY generated_at DESC
                    LIMIT ?
                """,
                    (domain, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT blueprint_id as id, name, domain, agents_count, generated_at
                    FROM blueprints
                    ORDER BY generated_at DESC
                    LIMIT ?
                """,
                    (limit,),
                ).fetchall()

            return [dict(row) for row in rows]

    def save_evaluation(
        self,
        blueprint_id: str,
        evaluation: SuccessEvaluation,
    ) -> None:
        """Save evaluation to database."""
        data = evaluation.to_dict()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evaluations
                (blueprint_id, overall_success, overall_score, evaluated_at, data)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    blueprint_id,
                    1 if evaluation.overall_success else 0,
                    evaluation.overall_score,
                    evaluation.evaluated_at,
                    json.dumps(data, default=str),
                ),
            )

    def get_evaluations(
        self,
        blueprint_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get evaluations from database."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT data FROM evaluations
                WHERE blueprint_id = ?
                ORDER BY evaluated_at DESC
                LIMIT ?
            """,
                (blueprint_id, limit),
            ).fetchall()

            return [json.loads(row["data"]) for row in rows]

    def get_success_rate(self, blueprint_id: str) -> float:
        """Get overall success rate for a blueprint."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(overall_success) as successes
                FROM evaluations
                WHERE blueprint_id = ?
            """,
                (blueprint_id,),
            ).fetchone()

            if row and row["total"] > 0:
                return row["successes"] / row["total"]
            return 0.0

    def search_blueprints(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search blueprints by name or domain."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT blueprint_id as id, name, domain, agents_count, generated_at
                FROM blueprints
                WHERE name LIKE ? OR domain LIKE ?
                ORDER BY generated_at DESC
                LIMIT ?
            """,
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()

            return [dict(row) for row in rows]
