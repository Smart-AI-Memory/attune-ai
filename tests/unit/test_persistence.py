"""Tests for attune.persistence"""

import json
import sqlite3
from pathlib import Path

import pytest

from attune.metrics_collector import MetricsCollector
from attune.pattern_library import Pattern, PatternLibrary
from attune.pattern_persistence import PatternPersistence


class TestPatternPersistence:
    """Tests for PatternPersistence class."""

    def test_save_and_load_json(self, tmp_path):
        """Test saving and loading PatternLibrary to/from JSON."""
        # Create library with real patterns
        library = PatternLibrary()
        pattern1 = Pattern(
            id="test_pattern_1",
            agent_id="agent_1",
            pattern_type="algorithm",
            name="Test Pattern 1",
            description="First test pattern",
            context={"domain": "testing"},
            code="def test(): pass",
            confidence=0.8,
            tags=["test", "pattern"],
        )
        pattern2 = Pattern(
            id="test_pattern_2",
            agent_id="agent_2",
            pattern_type="workflow",
            name="Test Pattern 2",
            description="Second test pattern",
            confidence=0.9,
        )
        library.contribute_pattern("agent_1", pattern1)
        library.contribute_pattern("agent_2", pattern2)

        # Save to JSON
        json_file = tmp_path / "patterns.json"
        PatternPersistence.save_to_json(library, str(json_file))

        # Verify file exists
        assert json_file.exists()

        # Load from JSON
        loaded_library = PatternPersistence.load_from_json(str(json_file))

        # Verify patterns were restored
        assert len(loaded_library.patterns) == 2
        assert "test_pattern_1" in loaded_library.patterns
        assert "test_pattern_2" in loaded_library.patterns

        # Verify pattern data
        loaded_pattern1 = loaded_library.patterns["test_pattern_1"]
        assert loaded_pattern1.agent_id == "agent_1"
        assert loaded_pattern1.pattern_type == "algorithm"
        assert loaded_pattern1.name == "Test Pattern 1"
        assert loaded_pattern1.confidence == 0.8
        assert loaded_pattern1.tags == ["test", "pattern"]
        assert loaded_pattern1.code == "def test(): pass"

    def test_save_json_creates_valid_json(self, tmp_path):
        """Test that saved JSON is valid and contains expected structure."""
        library = PatternLibrary()
        pattern = Pattern(
            id="json_test",
            agent_id="test_agent",
            pattern_type="test",
            name="JSON Test",
            description="Test JSON structure",
        )
        library.contribute_pattern("test_agent", pattern)

        # Save to JSON
        json_file = tmp_path / "test.json"
        PatternPersistence.save_to_json(library, str(json_file))

        # Read and verify JSON structure
        with open(json_file) as f:
            data = json.load(f)

        assert "patterns" in data
        assert "agent_contributions" in data
        assert "metadata" in data
        assert data["metadata"]["pattern_count"] == 1
        assert data["metadata"]["version"] == "1.0"
        assert len(data["patterns"]) == 1

    def test_load_json_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file raises FileNotFoundError."""
        json_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            PatternPersistence.load_from_json(str(json_file))

    def test_save_and_load_sqlite(self, tmp_path):
        """Test saving and loading PatternLibrary to/from SQLite."""
        # Create library with real patterns
        library = PatternLibrary()
        pattern = Pattern(
            id="sqlite_test_1",
            agent_id="sqlite_agent",
            pattern_type="database",
            name="SQLite Test Pattern",
            description="Testing SQLite persistence",
            context={"db": "sqlite"},
            confidence=0.75,
            usage_count=5,
            success_count=4,
            failure_count=1,
            tags=["sqlite", "test"],
        )
        library.contribute_pattern("sqlite_agent", pattern)

        # Save to SQLite
        db_file = tmp_path / "patterns.db"
        PatternPersistence.save_to_sqlite(library, str(db_file))

        # Verify database file exists
        assert db_file.exists()

        # Load from SQLite
        loaded_library = PatternPersistence.load_from_sqlite(str(db_file))

        # Verify patterns were restored
        assert len(loaded_library.patterns) == 1
        assert "sqlite_test_1" in loaded_library.patterns

        # Verify pattern data
        loaded_pattern = loaded_library.patterns["sqlite_test_1"]
        assert loaded_pattern.agent_id == "sqlite_agent"
        assert loaded_pattern.pattern_type == "database"
        assert loaded_pattern.name == "SQLite Test Pattern"
        assert loaded_pattern.confidence == 0.75
        assert loaded_pattern.usage_count == 5
        assert loaded_pattern.success_count == 4
        assert loaded_pattern.failure_count == 1
        assert loaded_pattern.tags == ["sqlite", "test"]

    def test_sqlite_creates_tables(self, tmp_path):
        """Test that SQLite save creates required database tables."""
        library = PatternLibrary()
        db_file = tmp_path / "test.db"

        PatternPersistence.save_to_sqlite(library, str(db_file))

        # Verify tables exist
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "patterns" in tables
        assert "pattern_usage" in tables

        conn.close()

    def test_sqlite_insert_or_replace(self, tmp_path):
        """Test that saving same pattern ID updates existing record."""
        library = PatternLibrary()
        pattern = Pattern(
            id="update_test",
            agent_id="agent_1",
            pattern_type="test",
            name="Original Name",
            description="Original description",
        )
        library.contribute_pattern("agent_1", pattern)

        db_file = tmp_path / "test.db"

        # First save
        PatternPersistence.save_to_sqlite(library, str(db_file))

        # Modify pattern
        library.patterns["update_test"].name = "Updated Name"
        library.patterns["update_test"].usage_count = 10

        # Second save (should update)
        PatternPersistence.save_to_sqlite(library, str(db_file))

        # Load and verify update
        loaded = PatternPersistence.load_from_sqlite(str(db_file))
        assert loaded.patterns["update_test"].name == "Updated Name"
        assert loaded.patterns["update_test"].usage_count == 10

    def test_empty_library_persistence(self, tmp_path):
        """Test saving and loading empty PatternLibrary."""
        library = PatternLibrary()

        # Test JSON
        json_file = tmp_path / "empty.json"
        PatternPersistence.save_to_json(library, str(json_file))
        loaded_json = PatternPersistence.load_from_json(str(json_file))
        assert len(loaded_json.patterns) == 0

        # Test SQLite
        db_file = tmp_path / "empty.db"
        PatternPersistence.save_to_sqlite(library, str(db_file))
        loaded_sqlite = PatternPersistence.load_from_sqlite(str(db_file))
        assert len(loaded_sqlite.patterns) == 0


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_initialization(self, tmp_path):
        """Test MetricsCollector initialization."""
        db_file = tmp_path / "metrics.db"
        MetricsCollector(db_path=str(db_file))

        # Verify database file was created
        assert Path(db_file).exists()

        # Verify tables were created
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "metrics" in tables

    def test_record_metric(self, tmp_path):
        """Test recording a single metric."""
        db_file = tmp_path / "test.db"
        collector = MetricsCollector(db_path=str(db_file))

        # Record metric
        collector.record_metric(
            user_id="user_1",
            success=True,
            response_time_ms=250.5,
            metadata={"test": "data"},
        )

        # Verify metric was recorded
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM metrics WHERE user_id = 'user_1'")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_get_user_stats_no_data(self, tmp_path):
        """Test getting stats for user with no data."""
        db_file = tmp_path / "test.db"
        collector = MetricsCollector(db_path=str(db_file))

        stats = collector.get_user_stats("nonexistent_user")

        assert stats["total_operations"] == 0
        assert stats["success_rate"] == 0.0
        assert stats["avg_response_time_ms"] == 0.0
        assert stats["first_use"] is None
        assert stats["last_use"] is None

    def test_get_user_stats_with_data(self, tmp_path):
        """Test getting aggregated user statistics."""
        db_file = tmp_path / "test.db"
        collector = MetricsCollector(db_path=str(db_file))

        # Record multiple metrics
        collector.record_metric("stats_user", True, 100.0)
        collector.record_metric("stats_user", True, 200.0)
        collector.record_metric("stats_user", False, 150.0)
        collector.record_metric("stats_user", True, 300.0)

        # Get stats
        stats = collector.get_user_stats("stats_user")

        assert stats["total_operations"] == 4
        assert stats["success_rate"] == 0.75  # 3 successes / 4 total
        assert stats["avg_response_time_ms"] == 187.5  # (100+200+150+300)/4
        assert stats["first_use"] is not None
        assert stats["last_use"] is not None

    def test_record_metric_with_metadata(self, tmp_path):
        """Test recording metric with custom metadata."""
        db_file = tmp_path / "test.db"
        collector = MetricsCollector(db_path=str(db_file))

        metadata = {
            "bottlenecks_predicted": 3,
            "complexity_score": 0.85,
            "custom_field": "test_value",
        }

        collector.record_metric(
            user_id="meta_user",
            success=True,
            response_time_ms=250.0,
            metadata=metadata,
        )

        # Verify metadata was stored
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT metadata FROM metrics WHERE user_id = 'meta_user'")
        stored_metadata_json = cursor.fetchone()[0]
        conn.close()

        stored_metadata = json.loads(stored_metadata_json)
        assert stored_metadata == metadata

    def test_multiple_users_isolated(self, tmp_path):
        """Test that metrics for different users are isolated."""
        db_file = tmp_path / "test.db"
        collector = MetricsCollector(db_path=str(db_file))

        # Record metrics for two different users
        collector.record_metric("user_a", True, 100.0)
        collector.record_metric("user_a", True, 150.0)
        collector.record_metric("user_b", False, 200.0)

        # Get stats for user_a
        stats_a = collector.get_user_stats("user_a")
        assert stats_a["total_operations"] == 2
        assert stats_a["success_rate"] == 1.0

        # Get stats for user_b
        stats_b = collector.get_user_stats("user_b")
        assert stats_b["total_operations"] == 1
        assert stats_b["success_rate"] == 0.0
