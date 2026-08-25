"""Tests for attune.persistence"""

import json
import sqlite3
from pathlib import Path

import pytest

from attune.pattern_library import Pattern, PatternLibrary
from attune.persistence import MetricsCollector, PatternPersistence, StateManager
from attune.state_manager import CollaborationState


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


class TestStateManager:
    """Tests for StateManager class."""

    def test_initialization(self, tmp_path):
        """Test StateManager initialization."""
        manager = StateManager(storage_path=str(tmp_path / "states"))

        assert manager.storage_path.exists()
        assert manager.storage_path.is_dir()

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading CollaborationState."""
        manager = StateManager(storage_path=str(tmp_path))

        # Create state with real data
        state = CollaborationState()
        state.trust_level = 0.75
        state.total_interactions = 10
        state.successful_interventions = 8
        state.failed_interventions = 2
        state.trust_trajectory = [0.5, 0.6, 0.7, 0.75]
        state.shared_context = {"test_key": "test_value"}

        # Save state
        manager.save_state("user_123", state)

        # Verify file was created
        state_file = tmp_path / "user_123.json"
        assert state_file.exists()

        # Load state
        loaded_state = manager.load_state("user_123")

        # Verify loaded state
        assert loaded_state is not None
        assert loaded_state.trust_level == 0.75
        assert loaded_state.total_interactions == 10
        assert loaded_state.successful_interventions == 8
        assert loaded_state.failed_interventions == 2
        assert loaded_state.trust_trajectory == [0.5, 0.6, 0.7, 0.75]
        assert loaded_state.shared_context == {"test_key": "test_value"}

    def test_load_nonexistent_state(self, tmp_path):
        """Test loading state for user that doesn't exist."""
        manager = StateManager(storage_path=str(tmp_path))

        state = manager.load_state("nonexistent_user")

        assert state is None

    def test_list_users(self, tmp_path):
        """Test listing all users with saved state."""
        manager = StateManager(storage_path=str(tmp_path))

        # Save states for multiple users
        state1 = CollaborationState()
        state2 = CollaborationState()
        state3 = CollaborationState()

        manager.save_state("user_1", state1)
        manager.save_state("user_2", state2)
        manager.save_state("user_3", state3)

        # List users
        users = manager.list_users()

        assert len(users) == 3
        assert "user_1" in users
        assert "user_2" in users
        assert "user_3" in users

    def test_delete_state(self, tmp_path):
        """Test deleting user state."""
        manager = StateManager(storage_path=str(tmp_path))

        # Save state
        state = CollaborationState()
        manager.save_state("delete_me", state)

        # Verify it exists
        assert manager.load_state("delete_me") is not None

        # Delete state
        deleted = manager.delete_state("delete_me")

        assert deleted is True
        assert manager.load_state("delete_me") is None

    def test_delete_nonexistent_state(self, tmp_path):
        """Test deleting state that doesn't exist."""
        manager = StateManager(storage_path=str(tmp_path))

        deleted = manager.delete_state("nonexistent")

        assert deleted is False

    def test_save_state_creates_valid_json(self, tmp_path):
        """Test that saved state JSON has expected structure."""
        manager = StateManager(storage_path=str(tmp_path))

        state = CollaborationState()
        state.trust_level = 0.8

        manager.save_state("json_test", state)

        # Read and verify JSON
        state_file = tmp_path / "json_test.json"
        with open(state_file) as f:
            data = json.load(f)

        assert "user_id" in data
        assert "trust_level" in data
        assert "total_interactions" in data
        assert "successful_interventions" in data
        assert "failed_interventions" in data
        assert "session_start" in data
        assert "trust_trajectory" in data
        assert "shared_context" in data
        assert "saved_at" in data
        assert data["trust_level"] == 0.8

    def test_load_corrupted_state_returns_none(self, tmp_path):
        """Test loading corrupted state file returns None."""
        manager = StateManager(storage_path=str(tmp_path))

        # Create corrupted JSON file
        corrupted_file = tmp_path / "corrupted.json"
        corrupted_file.write_text("{ invalid json }")

        state = manager.load_state("corrupted")

        assert state is None


class TestCollaborationState:
    """Tests for the CollaborationState model relocated into state_manager."""

    def test_defaults(self):
        """A fresh state starts neutral with empty history."""
        state = CollaborationState()

        assert state.trust_level == 0.5
        assert state.successful_interventions == 0
        assert state.failed_interventions == 0
        assert state.total_interactions == 0
        assert state.trust_trajectory == []

    def test_update_trust_success_increases_trust(self):
        """A successful outcome raises trust and records the interaction."""
        state = CollaborationState()

        state.update_trust("success")

        assert state.trust_level == 0.55  # 0.5 + 0.05 building rate
        assert state.successful_interventions == 1
        assert state.failed_interventions == 0
        assert state.total_interactions == 1
        assert state.trust_trajectory == [0.55]

    def test_update_trust_failure_decreases_trust(self):
        """A failed outcome erodes trust faster than success builds it."""
        state = CollaborationState()

        state.update_trust("failure")

        assert state.trust_level == 0.4  # 0.5 - 0.10 erosion rate
        assert state.failed_interventions == 1
        assert state.successful_interventions == 0
        assert state.total_interactions == 1
        assert state.trust_trajectory == [0.4]

    def test_update_trust_unknown_outcome_is_noop_on_stocks(self):
        """An unrecognized outcome leaves trust unchanged but still counts."""
        state = CollaborationState()

        state.update_trust("ignored")

        assert state.trust_level == 0.5
        assert state.successful_interventions == 0
        assert state.failed_interventions == 0
        assert state.total_interactions == 1
        assert state.trust_trajectory == [0.5]

    def test_update_trust_clamps_to_upper_bound(self):
        """Repeated successes never push trust above 1.0."""
        state = CollaborationState()

        for _ in range(50):
            state.update_trust("success")

        assert state.trust_level == 1.0

    def test_update_trust_clamps_to_lower_bound(self):
        """Repeated failures never push trust below 0.0."""
        state = CollaborationState()

        for _ in range(50):
            state.update_trust("failure")

        assert state.trust_level == 0.0

    def test_current_level_aliases_trust_level(self):
        """The current_level property mirrors trust_level."""
        state = CollaborationState()
        state.trust_level = 0.73

        assert state.current_level == 0.73


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
