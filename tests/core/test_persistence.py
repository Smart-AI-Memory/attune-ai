"""Tests for Persistence Module

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest

from attune import (
    MetricsCollector,
    Pattern,
    PatternLibrary,
    PatternPersistence,
    StateManager,
)
from attune.state_manager import CollaborationState


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)


@pytest.fixture
def sample_library():
    """Create sample pattern library for testing"""
    library = PatternLibrary()

    pattern1 = Pattern(
        id="test_001",
        agent_id="agent1",
        pattern_type="sequential",
        name="Test Pattern 1",
        description="A test pattern",
        context={"environment": "test"},
        code="def example(): pass",
        tags=["test", "sample"],
    )

    pattern2 = Pattern(
        id="test_002",
        agent_id="agent2",
        pattern_type="conditional",
        name="Test Pattern 2",
        description="Another test pattern",
        context={"environment": "production"},
        code="def another(): pass",
        tags=["test", "production"],
    )

    library.contribute_pattern("agent1", pattern1)
    library.contribute_pattern("agent2", pattern2)

    # Record some usage
    library.record_pattern_outcome("test_001", success=True)
    library.record_pattern_outcome("test_001", success=True)
    library.record_pattern_outcome("test_002", success=False)

    return library


class TestPatternPersistenceJSON:
    """Test JSON persistence for PatternLibrary"""

    def test_save_to_json(self, sample_library, temp_dir):
        """Test saving pattern library to JSON"""
        filepath = Path(temp_dir) / "patterns.json"

        PatternPersistence.save_to_json(sample_library, str(filepath))

        assert filepath.exists()

        # Verify JSON structure
        with open(filepath) as f:
            data = json.load(f)

        assert "patterns" in data
        assert "agent_contributions" in data
        assert "metadata" in data
        assert len(data["patterns"]) == 2
        assert data["metadata"]["pattern_count"] == 2

    def test_load_from_json(self, sample_library, temp_dir):
        """Test loading pattern library from JSON"""
        filepath = Path(temp_dir) / "patterns.json"

        # Save then load
        PatternPersistence.save_to_json(sample_library, str(filepath))
        loaded_library = PatternPersistence.load_from_json(str(filepath))

        # Verify patterns restored
        assert len(loaded_library.patterns) == 2
        assert "test_001" in loaded_library.patterns
        assert "test_002" in loaded_library.patterns

        # Verify pattern details
        pattern1 = loaded_library.patterns["test_001"]
        assert pattern1.name == "Test Pattern 1"
        assert pattern1.success_count == 2
        assert pattern1.usage_count == 2

        pattern2 = loaded_library.patterns["test_002"]
        assert pattern2.name == "Test Pattern 2"
        assert pattern2.success_count == 0
        assert pattern2.usage_count == 1

    def test_round_trip_json(self, sample_library, temp_dir):
        """Test save and load preserves all data"""
        filepath = Path(temp_dir) / "patterns.json"

        # Save
        PatternPersistence.save_to_json(sample_library, str(filepath))

        # Load
        loaded = PatternPersistence.load_from_json(str(filepath))

        # Verify exact match
        assert len(loaded.patterns) == len(sample_library.patterns)

        for pattern_id in sample_library.patterns:
            orig = sample_library.patterns[pattern_id]
            restored = loaded.patterns[pattern_id]

            assert orig.id == restored.id
            assert orig.name == restored.name
            assert orig.description == restored.description
            assert orig.context == restored.context
            assert orig.pattern_type == restored.pattern_type
            assert orig.code == restored.code
            assert orig.tags == restored.tags
            assert orig.agent_id == restored.agent_id
            assert orig.success_count == restored.success_count
            assert orig.usage_count == restored.usage_count

    def test_load_nonexistent_json(self, temp_dir):
        """Test loading from nonexistent file raises error"""
        filepath = Path(temp_dir) / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            PatternPersistence.load_from_json(str(filepath))

    def test_load_corrupt_json(self, temp_dir):
        """Test loading corrupt JSON raises error"""
        filepath = Path(temp_dir) / "corrupt.json"

        with open(filepath, "w") as f:
            f.write("not valid json{")

        with pytest.raises(json.JSONDecodeError):
            PatternPersistence.load_from_json(str(filepath))


class TestPatternPersistenceSQLite:
    """Test SQLite persistence for PatternLibrary"""

    def test_save_to_sqlite(self, sample_library, temp_dir):
        """Test saving pattern library to SQLite"""
        db_path = Path(temp_dir) / "patterns.db"

        PatternPersistence.save_to_sqlite(sample_library, str(db_path))

        assert db_path.exists()

        # Verify database structure
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "patterns" in tables
        assert "pattern_usage" in tables

        # Verify pattern count
        cursor.execute("SELECT COUNT(*) FROM patterns")
        count = cursor.fetchone()[0]
        assert count == 2

        conn.close()

    def test_load_from_sqlite(self, sample_library, temp_dir):
        """Test loading pattern library from SQLite"""
        db_path = Path(temp_dir) / "patterns.db"

        # Save then load
        PatternPersistence.save_to_sqlite(sample_library, str(db_path))
        loaded_library = PatternPersistence.load_from_sqlite(str(db_path))

        # Verify patterns restored
        assert len(loaded_library.patterns) == 2
        assert "test_001" in loaded_library.patterns
        assert "test_002" in loaded_library.patterns

    def test_round_trip_sqlite(self, sample_library, temp_dir):
        """Test SQLite save and load preserves all data"""
        db_path = Path(temp_dir) / "patterns.db"

        # Save
        PatternPersistence.save_to_sqlite(sample_library, str(db_path))

        # Load
        loaded = PatternPersistence.load_from_sqlite(str(db_path))

        # Verify exact match
        for pattern_id in sample_library.patterns:
            orig = sample_library.patterns[pattern_id]
            restored = loaded.patterns[pattern_id]

            assert orig.id == restored.id
            assert orig.name == restored.name
            assert orig.tags == restored.tags
            assert orig.success_count == restored.success_count

    def test_sqlite_update(self, sample_library, temp_dir):
        """Test updating existing patterns in SQLite"""
        db_path = Path(temp_dir) / "patterns.db"

        # Initial save
        PatternPersistence.save_to_sqlite(sample_library, str(db_path))

        # Update pattern usage
        sample_library.record_pattern_outcome("test_001", success=True)

        # Save again
        PatternPersistence.save_to_sqlite(sample_library, str(db_path))

        # Load and verify update
        loaded = PatternPersistence.load_from_sqlite(str(db_path))
        pattern = loaded.patterns["test_001"]
        assert pattern.success_count == 3  # Was 2, now 3


class TestStateManager:
    """Test StateManager for collaboration state persistence"""

    def test_save_state(self, temp_dir):
        """Test saving collaboration state"""
        manager = StateManager(storage_path=temp_dir)

        state = CollaborationState()
        state.update_trust("success")
        state.update_trust("success")

        manager.save_state("test_user", state)

        # Verify file created
        filepath = Path(temp_dir) / "test_user.json"
        assert filepath.exists()

        # Verify content
        with open(filepath) as f:
            data = json.load(f)

        assert data["user_id"] == "test_user"
        assert data["trust_level"] > 0.5  # Increased from default
        assert data["total_interactions"] == 2

    def test_load_state(self, temp_dir):
        """Test loading collaboration state"""
        manager = StateManager(storage_path=temp_dir)

        # Create and save state
        state = CollaborationState()
        state.update_trust("success")
        manager.save_state("test_user", state)

        # Load state
        loaded_state = manager.load_state("test_user")

        assert loaded_state is not None
        assert loaded_state.total_interactions == 1
        assert loaded_state.trust_level > 0.5

    def test_load_nonexistent_state(self, temp_dir):
        """Test loading nonexistent state returns None"""
        manager = StateManager(storage_path=temp_dir)

        state = manager.load_state("nonexistent_user")

        assert state is None

    def test_list_users(self, temp_dir):
        """Test listing all users with saved state"""
        manager = StateManager(storage_path=temp_dir)

        # Save states for multiple users
        for user_id in ["user1", "user2", "user3"]:
            manager.save_state(user_id, CollaborationState())

        users = manager.list_users()

        assert len(users) == 3
        assert "user1" in users
        assert "user2" in users
        assert "user3" in users

    def test_delete_state(self, temp_dir):
        """Test deleting user state"""
        manager = StateManager(storage_path=temp_dir)

        # Save state
        manager.save_state("test_user", CollaborationState())

        # Delete
        deleted = manager.delete_state("test_user")
        assert deleted is True

        # Verify deleted
        state = manager.load_state("test_user")
        assert state is None

        # Delete again returns False
        deleted_again = manager.delete_state("test_user")
        assert deleted_again is False

    def test_round_trip_state(self, temp_dir):
        """Test state save/load preserves all fields"""
        manager = StateManager(storage_path=temp_dir)

        # Create state with specific values
        state = CollaborationState()
        state.trust_level = 0.75
        state.total_interactions = 10
        state.successful_interventions = 8
        state.failed_interventions = 2
        state.shared_context = {"key": "value"}

        # Save and load
        manager.save_state("test_user", state)
        loaded_state = manager.load_state("test_user")

        # Verify all fields
        assert loaded_state.trust_level == 0.75
        assert loaded_state.total_interactions == 10
        assert loaded_state.successful_interventions == 8
        assert loaded_state.failed_interventions == 2
        assert loaded_state.shared_context == {"key": "value"}

    def test_load_state_corrupted_json(self, temp_dir):
        """Test load_state with corrupted JSON returns None (lines 346-348)"""
        manager = StateManager(storage_path=temp_dir)

        # Create a corrupted JSON file
        filepath = Path(temp_dir) / "corrupted_user.json"
        with open(filepath, "w") as f:
            f.write("{invalid json syntax")

        # Should return None without crashing
        state = manager.load_state("corrupted_user")
        assert state is None

    def test_load_state_missing_key(self, temp_dir):
        """Test load_state with missing required key returns None"""
        manager = StateManager(storage_path=temp_dir)

        # Create a JSON file missing required keys
        filepath = Path(temp_dir) / "incomplete_user.json"
        with open(filepath, "w") as f:
            json.dump({"user_id": "incomplete_user"}, f)  # Missing trust_level, etc.

        # Should return None due to KeyError
        state = manager.load_state("incomplete_user")
        assert state is None

    def test_load_state_invalid_date_format(self, temp_dir):
        """Test load_state with invalid date format returns None"""
        manager = StateManager(storage_path=temp_dir)

        # Create a JSON file with invalid date format
        filepath = Path(temp_dir) / "bad_date_user.json"
        data = {
            "user_id": "bad_date_user",
            "trust_level": 0.5,
            "total_interactions": 1,
            "successful_interventions": 1,
            "failed_interventions": 0,
            "session_start": "not-a-valid-date-format",
            "trust_trajectory": [],
            "shared_context": {},
        }
        with open(filepath, "w") as f:
            json.dump(data, f)

        # Should return None due to ValueError in datetime.fromisoformat
        state = manager.load_state("bad_date_user")
        assert state is None


class TestMetricsCollector:
    """Test MetricsCollector for telemetry"""

    def test_record_metric(self, temp_dir):
        """Test recording a single metric"""
        db_path = str(Path(temp_dir) / "metrics.db")
        collector = MetricsCollector(db_path=db_path)

        collector.record_metric(
            user_id="test_user",
            success=True,
            response_time_ms=250.5,
            metadata={"bottlenecks": 3},
        )

        # Verify recorded
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metrics")
        count = cursor.fetchone()[0]
        assert count == 1
        conn.close()

    def test_get_user_stats(self, temp_dir):
        """Test getting aggregated user statistics"""
        db_path = str(Path(temp_dir) / "metrics.db")
        collector = MetricsCollector(db_path=db_path)

        # Record multiple metrics
        for i in range(10):
            collector.record_metric(
                user_id="test_user",
                success=(i % 5 != 0),  # 8 successes, 2 failures (i=0,5 are failures)
                response_time_ms=200.0 + i * 10,
            )

        stats = collector.get_user_stats("test_user")

        assert stats["total_operations"] == 10
        assert stats["success_rate"] == pytest.approx(0.8, abs=0.01)  # 8/10
        assert stats["avg_response_time_ms"] > 200
        assert stats["first_use"] is not None
        assert stats["last_use"] is not None

    def test_legacy_level_column_migrated(self, temp_dir):
        """A pre-15.0.0 DB with the empathy_level column still accepts inserts."""
        db_path = str(Path(temp_dir) / "legacy.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                empathy_level INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                response_time_ms REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        conn.execute("CREATE INDEX idx_user_level ON metrics(user_id, empathy_level)")
        conn.execute(
            "INSERT INTO metrics (user_id, empathy_level, success, response_time_ms)"
            " VALUES ('old_user', 3, 1, 100.0)"
        )
        conn.commit()
        conn.close()

        collector = MetricsCollector(db_path=db_path)

        # The legacy column and its index must actually be gone — a
        # compat workaround keeping the old schema would pass the
        # insert below while leaving the migration undone.
        conn = sqlite3.connect(db_path)
        columns = [row[1] for row in conn.execute("PRAGMA table_info(metrics)")]
        assert "empathy_level" not in columns
        indexes = [row[1] for row in conn.execute("PRAGMA index_list(metrics)")]
        assert "idx_user_level" not in indexes
        conn.close()

        collector.record_metric(
            user_id="old_user",
            success=True,
            response_time_ms=120.0,
        )

        stats = collector.get_user_stats("old_user")
        assert stats["total_operations"] == 2

    def test_legacy_migration_rebuild_fallback(self, temp_dir):
        """SQLite < 3.35 has no DROP COLUMN — the rebuild path preserves rows.

        Forces the fallback by refusing the DROP COLUMN statement the way
        an old SQLite would, then runs the real rebuild SQL against a real
        database so the migration is proven, not merely reachable.
        """
        db_path = str(Path(temp_dir) / "old_sqlite.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                empathy_level INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                response_time_ms REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """
        )
        conn.execute("CREATE INDEX idx_user_level ON metrics(user_id, empathy_level)")
        conn.execute(
            "INSERT INTO metrics (user_id, empathy_level, success, response_time_ms, metadata)"
            " VALUES ('kept_user', 4, 1, 100.0, '{\"a\": 1}')"
        )
        conn.commit()

        class _NoDropColumnCursor:
            """Delegates to a real cursor but rejects DROP COLUMN."""

            def __init__(self, cursor):
                self._cursor = cursor

            def execute(self, sql, *args):
                if "DROP COLUMN" in sql:
                    raise sqlite3.OperationalError('near "DROP": syntax error')
                return self._cursor.execute(sql, *args)

        MetricsCollector._migrate_legacy_level_column(_NoDropColumnCursor(conn.cursor()))
        conn.commit()

        columns = [row[1] for row in conn.execute("PRAGMA table_info(metrics)")]
        assert "empathy_level" not in columns
        assert set(columns) == {
            "id",
            "user_id",
            "success",
            "response_time_ms",
            "timestamp",
            "metadata",
        }

        # The rebuild must carry the existing rows across, not drop them.
        row = conn.execute(
            "SELECT id, user_id, success, response_time_ms, metadata FROM metrics"
        ).fetchall()
        assert row == [(1, "kept_user", 1, 100.0, '{"a": 1}')]
        conn.close()

        # The migrated database still works through the public API.
        collector = MetricsCollector(db_path=db_path)
        collector.record_metric(user_id="kept_user", success=True, response_time_ms=120.0)
        assert collector.get_user_stats("kept_user")["total_operations"] == 2

    def test_get_nonexistent_user_stats(self, temp_dir):
        """Test getting stats for nonexistent user returns empty"""
        db_path = str(Path(temp_dir) / "metrics.db")
        collector = MetricsCollector(db_path=db_path)

        stats = collector.get_user_stats("nonexistent_user")

        assert stats["total_operations"] == 0
        assert stats["success_rate"] == 0.0

    def test_metrics_with_metadata(self, temp_dir):
        """Test recording and storing metadata"""
        db_path = str(Path(temp_dir) / "metrics.db")
        collector = MetricsCollector(db_path=db_path)

        collector.record_metric(
            user_id="test_user",
            success=True,
            response_time_ms=300.0,
            metadata={"intervention_count": 5, "risk_level": "high"},
        )

        # Verify metadata stored
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM metrics WHERE user_id = ?", ("test_user",))
        metadata_json = cursor.fetchone()[0]
        conn.close()

        metadata = json.loads(metadata_json)
        assert metadata["intervention_count"] == 5
        assert metadata["risk_level"] == "high"
