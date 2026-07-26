"""Pattern Library Persistence (JSON and SQLite).

Provides save/load for PatternLibrary to JSON and SQLite formats.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import sqlite3
from datetime import datetime
from typing import Any

from attune.security.path_validation import _validate_file_path

from .pattern_library import Pattern, PatternLibrary


class PatternPersistence:
    """Save and load PatternLibrary to/from files

    Supports:
    - JSON format (human-readable, good for backups)
    - SQLite format (queryable, good for production)
    """

    @staticmethod
    def save_to_json(library: PatternLibrary, filepath: str):
        """Save pattern library to JSON file

        Args:
            library: PatternLibrary instance to save
            filepath: Path to JSON file

        Example:
            >>> library = PatternLibrary()
            >>> PatternPersistence.save_to_json(library, "patterns.json")

        """
        patterns_list: list[dict[str, Any]] = []
        data: dict[str, Any] = {
            "patterns": patterns_list,
            "agent_contributions": library.agent_contributions,
            "metadata": {
                "saved_at": datetime.now().isoformat(),
                "pattern_count": len(library.patterns),
                "version": "1.0",
            },
        }

        # Serialize each pattern
        for _pattern_id, pattern in library.patterns.items():
            patterns_list.append(
                {
                    "id": pattern.id,
                    "agent_id": pattern.agent_id,
                    "pattern_type": pattern.pattern_type,
                    "name": pattern.name,
                    "description": pattern.description,
                    "context": pattern.context,
                    "code": pattern.code,
                    "confidence": pattern.confidence,
                    "usage_count": pattern.usage_count,
                    "success_count": pattern.success_count,
                    "failure_count": pattern.failure_count,
                    "tags": pattern.tags,
                    "discovered_at": pattern.discovered_at.isoformat(),
                    "last_used": pattern.last_used.isoformat() if pattern.last_used else None,
                },
            )

        # Write to file
        validated_path = _validate_file_path(filepath)
        with open(validated_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_from_json(filepath: str) -> PatternLibrary:
        """Load pattern library from JSON file

        Args:
            filepath: Path to JSON file

        Returns:
            PatternLibrary instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON

        Example:
            >>> library = PatternPersistence.load_from_json("patterns.json")

        """
        validated_path = _validate_file_path(filepath)
        with open(validated_path) as f:
            data = json.load(f)

        library = PatternLibrary()

        # Restore patterns
        for pattern_data in data["patterns"]:
            pattern = Pattern(
                id=pattern_data["id"],
                agent_id=pattern_data["agent_id"],
                pattern_type=pattern_data["pattern_type"],
                name=pattern_data["name"],
                description=pattern_data["description"],
                context=pattern_data.get("context", {}),
                code=pattern_data.get("code"),
                confidence=pattern_data.get("confidence", 0.5),
                usage_count=pattern_data.get("usage_count", 0),
                success_count=pattern_data.get("success_count", 0),
                failure_count=pattern_data.get("failure_count", 0),
                tags=pattern_data.get("tags", []),
                discovered_at=datetime.fromisoformat(pattern_data["discovered_at"]),
                last_used=(
                    datetime.fromisoformat(pattern_data["last_used"])
                    if pattern_data.get("last_used")
                    else None
                ),
            )
            library.contribute_pattern(pattern.agent_id, pattern)

        # Restore agent_contributions index
        library.agent_contributions = data.get("agent_contributions", {})

        return library

    @staticmethod
    def save_to_sqlite(library: PatternLibrary, db_path: str):
        """Save pattern library to SQLite database

        Args:
            library: PatternLibrary instance to save
            db_path: Path to SQLite database file

        Creates tables:
            - patterns: Core pattern data
            - pattern_usage: Usage history

        Example:
            >>> library = PatternLibrary()
            >>> PatternPersistence.save_to_sqlite(library, "patterns.db")

        """
        validated_path = _validate_file_path(db_path)
        conn = sqlite3.connect(str(validated_path))
        cursor = conn.cursor()

        # Create tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                context TEXT,
                code TEXT,
                confidence REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                tags TEXT,
                discovered_at TIMESTAMP,
                last_used TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pattern_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pattern_id) REFERENCES patterns(id)
            )
        """,
        )

        # Insert or update patterns
        for pattern in library.patterns.values():
            cursor.execute(
                """
                INSERT OR REPLACE INTO patterns (
                    id, agent_id, pattern_type, name, description, context,
                    code, confidence, usage_count, success_count, failure_count,
                    tags, discovered_at, last_used, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    pattern.id,
                    pattern.agent_id,
                    pattern.pattern_type,
                    pattern.name,
                    pattern.description,
                    json.dumps(pattern.context),
                    pattern.code,
                    pattern.confidence,
                    pattern.usage_count,
                    pattern.success_count,
                    pattern.failure_count,
                    json.dumps(pattern.tags),
                    pattern.discovered_at.isoformat(),
                    pattern.last_used.isoformat() if pattern.last_used else None,
                ),
            )

        conn.commit()
        conn.close()

    @staticmethod
    def load_from_sqlite(db_path: str) -> PatternLibrary:
        """Load pattern library from SQLite database

        Args:
            db_path: Path to SQLite database file

        Returns:
            PatternLibrary instance

        Example:
            >>> library = PatternPersistence.load_from_sqlite("patterns.db")

        """
        validated_path = _validate_file_path(db_path)
        conn = sqlite3.connect(str(validated_path))
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()

        library = PatternLibrary()

        # Load patterns
        cursor.execute("SELECT * FROM patterns")
        rows = cursor.fetchall()

        for row in rows:
            pattern = Pattern(
                id=row["id"],
                agent_id=row["agent_id"],
                pattern_type=row["pattern_type"],
                name=row["name"],
                description=row["description"],
                context=json.loads(row["context"]),
                code=row["code"],
                confidence=row["confidence"],
                usage_count=row["usage_count"],
                success_count=row["success_count"],
                failure_count=row["failure_count"],
                tags=json.loads(row["tags"]),
                discovered_at=datetime.fromisoformat(row["discovered_at"]),
                last_used=datetime.fromisoformat(row["last_used"]) if row["last_used"] else None,
            )
            library.contribute_pattern(pattern.agent_id, pattern)

        conn.close()
        return library
