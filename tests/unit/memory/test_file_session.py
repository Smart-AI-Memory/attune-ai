"""Tests for file-based session memory.

Tests the FileSessionMemory class and file-first architecture features.
"""

import time
from pathlib import Path

import pytest

from attune.memory.file_session import (
    FileSessionConfig,
    FileSessionMemory,
    SessionState,
    StagedPatternFile,
    WorkingEntry,
    get_file_session_memory,
)


class TestFileSessionConfig:
    """Tests for FileSessionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FileSessionConfig()

        assert config.base_dir == ".attune"
        assert config.sessions_subdir == "sessions"
        assert config.patterns_subdir == "patterns"
        assert config.working_ttl_seconds == 3600
        assert config.pattern_ttl_seconds == 86400

    def test_sessions_dir_property(self):
        """Test sessions_dir computed property."""
        config = FileSessionConfig(base_dir="/tmp/test")

        assert config.sessions_dir == Path("/tmp/test/sessions")

    def test_patterns_dir_property(self):
        """Test patterns_dir computed property."""
        config = FileSessionConfig(base_dir="/tmp/test")

        assert config.patterns_dir == Path("/tmp/test/patterns")


class TestWorkingEntry:
    """Tests for WorkingEntry dataclass."""

    def test_not_expired_when_no_expiry(self):
        """Test entry without expiry is never expired."""
        entry = WorkingEntry(
            key="test",
            value={"data": 123},
            agent_id="agent1",
            stashed_at=time.time(),
            expires_at=None,
        )

        assert not entry.is_expired()

    def test_not_expired_when_future_expiry(self):
        """Test entry with future expiry is not expired."""
        entry = WorkingEntry(
            key="test",
            value={"data": 123},
            agent_id="agent1",
            stashed_at=time.time(),
            expires_at=time.time() + 3600,
        )

        assert not entry.is_expired()

    def test_expired_when_past_expiry(self):
        """Test entry with past expiry is expired."""
        entry = WorkingEntry(
            key="test",
            value={"data": 123},
            agent_id="agent1",
            stashed_at=time.time() - 7200,
            expires_at=time.time() - 3600,
        )

        assert entry.is_expired()

    def test_to_dict_round_trip(self):
        """Test serialization and deserialization."""
        entry = WorkingEntry(
            key="test",
            value={"nested": {"data": [1, 2, 3]}},
            agent_id="agent1",
            stashed_at=12345.0,
            expires_at=67890.0,
        )

        data = entry.to_dict()
        restored = WorkingEntry.from_dict(data)

        assert restored.key == entry.key
        assert restored.value == entry.value
        assert restored.agent_id == entry.agent_id
        assert restored.stashed_at == entry.stashed_at
        assert restored.expires_at == entry.expires_at


class TestStagedPatternFile:
    """Tests for StagedPatternFile dataclass."""

    def test_default_confidence(self):
        """Test default confidence is 0.5."""
        pattern = StagedPatternFile(
            pattern_id="pat_001",
            agent_id="agent1",
            pattern_type="security",
            name="Test Pattern",
            description="A test pattern",
        )

        assert pattern.confidence == 0.5

    def test_not_expired_when_no_expiry(self):
        """Test pattern without expiry is never expired."""
        pattern = StagedPatternFile(
            pattern_id="pat_001",
            agent_id="agent1",
            pattern_type="security",
            name="Test Pattern",
            description="A test pattern",
            expires_at=None,
        )

        assert not pattern.is_expired()

    def test_to_dict_round_trip(self):
        """Test serialization and deserialization."""
        pattern = StagedPatternFile(
            pattern_id="pat_001",
            agent_id="agent1",
            pattern_type="security",
            name="Test Pattern",
            description="A test pattern",
            code="def safe_query(): pass",
            confidence=0.85,
            metadata={"source": "test"},
        )

        data = pattern.to_dict()
        restored = StagedPatternFile.from_dict(data)

        assert restored.pattern_id == pattern.pattern_id
        assert restored.name == pattern.name
        assert restored.confidence == pattern.confidence
        assert restored.code == pattern.code


class TestSessionState:
    """Tests for SessionState dataclass."""

    def test_new_session(self):
        """Test creating a new session state."""
        state = SessionState.new("test_user")

        assert state.user_id == "test_user"
        assert state.session_id.startswith("session_")
        assert state.started_at > 0
        assert state.last_updated > 0
        assert len(state.working_memory) == 0
        assert len(state.staged_patterns) == 0

    def test_to_dict_round_trip(self):
        """Test serialization and deserialization."""
        state = SessionState.new("test_user")
        state.working_memory["key1"] = WorkingEntry(
            key="key1",
            value="value1",
            agent_id="test_user",
            stashed_at=time.time(),
        )
        state.context["task"] = "testing"

        data = state.to_dict()
        restored = SessionState.from_dict(data)

        assert restored.session_id == state.session_id
        assert restored.user_id == state.user_id
        assert "key1" in restored.working_memory
        assert restored.context["task"] == "testing"


class TestFileSessionMemory:
    """Tests for FileSessionMemory class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return str(tmp_path / "empathy_test")

    @pytest.fixture
    def memory(self, temp_storage):
        """Create FileSessionMemory instance."""
        config = FileSessionConfig(base_dir=temp_storage)
        mem = FileSessionMemory(user_id="test_user", config=config)
        yield mem
        mem.close()

    def test_initialization_creates_directories(self, temp_storage):
        """Test that initialization creates required directories."""
        config = FileSessionConfig(base_dir=temp_storage)
        memory = FileSessionMemory(user_id="test_user", config=config)

        assert Path(temp_storage).exists()
        assert (Path(temp_storage) / "sessions").exists()
        assert (Path(temp_storage) / "patterns").exists()
        assert (Path(temp_storage) / "patterns" / "staged").exists()
        assert (Path(temp_storage) / "patterns" / "promoted").exists()

        memory.close()

    def test_stash_and_retrieve(self, memory):
        """Test storing and retrieving data."""
        memory.stash("test_key", {"value": 42})

        result = memory.retrieve("test_key")

        assert result == {"value": 42}

    def test_retrieve_nonexistent_key(self, memory):
        """Test retrieving a key that doesn't exist."""
        result = memory.retrieve("nonexistent")

        assert result is None

    def test_stash_with_ttl_expires(self, memory):
        """Test that data with TTL expires."""
        memory.stash("short_lived", "data", ttl=1)

        # Should exist immediately
        assert memory.retrieve("short_lived") == "data"

        # Wait for expiration
        time.sleep(1.5)

        # Should be gone
        assert memory.retrieve("short_lived") is None

    def test_delete_key(self, memory):
        """Test deleting a key."""
        memory.stash("to_delete", "value")
        assert memory.retrieve("to_delete") == "value"

        memory.delete("to_delete")

        assert memory.retrieve("to_delete") is None

    def test_delete_nonexistent_key_returns_false(self, memory):
        """Test deleting a key that was never stashed returns False."""
        assert memory.delete("never_stashed") is False

    def test_keys_pattern_matching(self, memory):
        """Test keys() with pattern matching."""
        memory.stash("prefix_one", 1)
        memory.stash("prefix_two", 2)
        memory.stash("other_key", 3)

        prefix_keys = memory.keys("prefix_*")

        assert len(prefix_keys) == 2
        assert "prefix_one" in prefix_keys
        assert "prefix_two" in prefix_keys

    def test_stage_pattern(self, memory):
        """Test staging a pattern."""
        success = memory.stage_pattern(
            pattern_id="sec_001",
            pattern_type="security",
            name="SQL Injection Prevention",
            description="Always use parameterized queries",
            confidence=0.9,
        )

        assert success is True

        staged = memory.get_staged_patterns()
        assert len(staged) == 1
        assert staged[0].pattern_id == "sec_001"
        assert staged[0].confidence == 0.9

    def test_staged_patterns_sorted_by_confidence(self, memory):
        """Test that staged patterns are sorted by confidence (descending)."""
        memory.stage_pattern(
            pattern_id="low",
            pattern_type="general",
            name="Low Confidence",
            description="Low",
            confidence=0.3,
        )
        memory.stage_pattern(
            pattern_id="high",
            pattern_type="general",
            name="High Confidence",
            description="High",
            confidence=0.9,
        )
        memory.stage_pattern(
            pattern_id="mid",
            pattern_type="general",
            name="Mid Confidence",
            description="Mid",
            confidence=0.6,
        )

        staged = memory.get_staged_patterns()

        assert staged[0].pattern_id == "high"
        assert staged[1].pattern_id == "mid"
        assert staged[2].pattern_id == "low"

    def test_promote_pattern(self, memory):
        """Test promoting a pattern."""
        memory.stage_pattern(
            pattern_id="to_promote",
            pattern_type="security",
            name="Promotable Pattern",
            description="High confidence pattern",
            confidence=0.85,
        )

        success, pattern, message = memory.promote_pattern("to_promote", min_confidence=0.8)

        assert success is True
        assert pattern is not None
        assert pattern.pattern_id == "to_promote"
        assert "promoted" in message.lower()

        # Should be removed from staged
        staged = memory.get_staged_patterns()
        assert len(staged) == 0

    def test_promote_pattern_below_threshold(self, memory):
        """Test promoting a pattern below confidence threshold."""
        memory.stage_pattern(
            pattern_id="low_conf",
            pattern_type="general",
            name="Low Confidence",
            description="Below threshold",
            confidence=0.5,
        )

        success, pattern, message = memory.promote_pattern("low_conf", min_confidence=0.8)

        assert success is False
        assert pattern is None
        assert "below" in message.lower() or "confidence" in message.lower()

    def test_context_management(self, memory):
        """Test context storage."""
        memory.set_context("task", "testing")
        memory.set_context("phase", "implementation")

        assert memory.get_context("task") == "testing"
        assert memory.get_context("phase") == "implementation"
        assert memory.get_context("nonexistent") is None
        assert memory.get_context("nonexistent", "default") == "default"

    def test_get_all_context(self, memory):
        """Test getting all context."""
        memory.set_context("key1", "value1")
        memory.set_context("key2", "value2")

        context = memory.get_all_context()

        assert context == {"key1": "value1", "key2": "value2"}

    def test_get_stats(self, memory):
        """Test getting statistics."""
        memory.stash("key1", "value1")
        memory.stash("key2", "value2")
        memory.set_context("ctx", "value")
        memory.stage_pattern(
            pattern_id="pat",
            pattern_type="general",
            name="Pattern",
            description="Test",
        )

        stats = memory.get_stats()

        assert stats["mode"] == "file"
        assert stats["working_keys"] == 2
        assert stats["context_keys"] == 1
        assert stats["staged_patterns"] == 1
        assert stats["user_id"] == "test_user"

    def test_is_connected_always_true(self, memory):
        """Test that is_connected is always True for file-based memory."""
        assert memory.is_connected() is True

    def test_supports_realtime_false(self, memory):
        """Test that real-time features are not supported."""
        assert memory.supports_realtime() is False
        assert memory.supports_distributed() is False

    def test_session_persistence(self, temp_storage):
        """Test that session data persists across instances."""
        config = FileSessionConfig(base_dir=temp_storage)

        # First session - store data
        memory1 = FileSessionMemory(user_id="test_user", config=config)
        memory1.stash("persistent_key", {"saved": True}, ttl=3600)
        memory1.set_context("important", "data")
        session_id = memory1._state.session_id
        memory1.close()

        # Second session - should restore
        memory2 = FileSessionMemory(user_id="test_user", config=config)

        assert memory2._state.session_id == session_id
        assert memory2.retrieve("persistent_key") == {"saved": True}
        assert memory2.get_context("important") == "data"

        memory2.close()

    def test_context_manager(self, temp_storage):
        """Test using FileSessionMemory as context manager."""
        config = FileSessionConfig(base_dir=temp_storage)

        with FileSessionMemory(user_id="test_user", config=config) as memory:
            memory.stash("key", "value")
            assert memory.retrieve("key") == "value"

        # After context exit, memory should be closed
        # (we can't easily test this, but at least verify no exception)


class TestGetFileSessionMemory:
    """Tests for get_file_session_memory factory function."""

    def test_creates_memory_with_defaults(self, tmp_path):
        """Test factory function with default settings."""
        base_dir = str(tmp_path / "empathy")

        memory = get_file_session_memory(user_id="test_user", base_dir=base_dir)

        assert memory.user_id == "test_user"
        assert memory.config.base_dir == base_dir
        assert memory.is_connected()

        memory.close()

    def test_creates_memory_with_custom_settings(self, tmp_path):
        """Test factory function with custom settings."""
        base_dir = str(tmp_path / "custom")

        memory = get_file_session_memory(
            user_id="custom_user",
            base_dir=base_dir,
            working_ttl_seconds=7200,
            pattern_ttl_seconds=172800,
        )

        assert memory.config.working_ttl_seconds == 7200
        assert memory.config.pattern_ttl_seconds == 172800

        memory.close()


class TestFileFirstIntegration:
    """Integration tests for file-first architecture."""

    def test_unified_memory_file_first(self, tmp_path):
        """Test UnifiedMemory with file-first configuration."""
        from attune.memory import MemoryConfig, UnifiedMemory

        config = MemoryConfig(
            file_session_enabled=True,
            file_session_dir=str(tmp_path / "empathy"),
            redis_auto_start=False,
            redis_required=False,
        )

        memory = UnifiedMemory(user_id="test_user", config=config)

        # Should have file session but may not have Redis
        assert memory.has_file_session
        assert memory.supports_persistence()

        # Stash and retrieve should work
        memory.stash("test", {"data": 123})
        assert memory.retrieve("test") == {"data": 123}

        memory.close()

    def test_capabilities_without_redis(self, tmp_path):
        """Test capability detection without Redis."""
        from attune.memory import MemoryConfig, UnifiedMemory

        config = MemoryConfig(
            file_session_enabled=True,
            file_session_dir=str(tmp_path / "empathy"),
            redis_mock=True,  # Force mock mode
            redis_required=False,
        )

        memory = UnifiedMemory(user_id="test_user", config=config)

        caps = memory.get_capabilities()

        assert caps["file_session"] is True
        assert caps["persistence"] is True
        # Redis-dependent features should be False without real Redis
        assert caps["realtime"] is False
        assert caps["distributed"] is False

        memory.close()

    def test_compact_state_generation(self, tmp_path):
        """Test compact state generation."""
        from attune.memory import MemoryConfig, UnifiedMemory

        config = MemoryConfig(
            file_session_enabled=True,
            file_session_dir=str(tmp_path / "empathy"),
            redis_auto_start=False,
            auto_generate_compact_state=False,  # Manual generation
            compact_state_path=str(tmp_path / "compact-state.md"),
        )

        memory = UnifiedMemory(user_id="test_user", config=config)

        # Set handoff context
        memory.set_handoff(
            situation="Testing file-first architecture",
            background="Unit test execution",
            assessment="All tests passing",
            recommendation="Continue development",
        )

        # Generate compact state
        content = memory.generate_compact_state()

        assert "Compact State" in content
        assert "Work Handoff" in content
        assert "Testing file-first architecture" in content
        assert "Unit test execution" in content

        memory.close()

    def test_export_to_claude_md(self, tmp_path):
        """Test exporting to Claude.md file."""
        from attune.memory import MemoryConfig, UnifiedMemory

        output_path = tmp_path / "claude" / "compact-state.md"
        config = MemoryConfig(
            file_session_enabled=True,
            file_session_dir=str(tmp_path / "empathy"),
            redis_auto_start=False,
            auto_generate_compact_state=False,
            compact_state_path=str(output_path),
        )

        memory = UnifiedMemory(user_id="test_user", config=config)

        # Export
        result_path = memory.export_to_claude_md()

        assert result_path.exists()
        content = result_path.read_text()
        assert "Compact State" in content

        memory.close()


class TestFileSessionMemoryCoverageGaps:
    """Targeted tests for branches not exercised elsewhere in this file.

    Covers: resuming a session by explicit id through the facade
    constructor, the defensive re-check inside retrieve() for an
    entry that expires between cleanup and use, get_recent_sessions()
    (gzip archive, plain-json archive, corrupt-file tolerance, limit
    truncation), and the Redis-compatibility no-ops (use_mock,
    publish, subscribe).
    """

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return str(tmp_path / "coverage_test")

    @pytest.fixture
    def memory(self, temp_storage):
        """Create FileSessionMemory instance."""
        config = FileSessionConfig(base_dir=temp_storage)
        mem = FileSessionMemory(user_id="test_user", config=config)
        yield mem
        mem.close()

    # =========================================================================
    # __init__ session_id resume path
    # =========================================================================

    def test_resume_specific_session_via_constructor(self, temp_storage):
        """Passing session_id to the constructor resumes that session."""
        config = FileSessionConfig(base_dir=temp_storage)

        first = FileSessionMemory(user_id="test_user", config=config)
        first.stash("resumed_key", "resumed_value")
        session_id = first._state.session_id
        first.close()

        resumed = FileSessionMemory(
            user_id="test_user",
            config=config,
            session_id=session_id,
        )

        assert resumed._state.session_id == session_id
        assert resumed.retrieve("resumed_key") == "resumed_value"

        resumed.close()

    # =========================================================================
    # retrieve() defensive expiry branch
    # =========================================================================

    def test_retrieve_removes_entry_that_expires_after_cleanup(self, memory):
        """An entry found expired at the post-cleanup check is deleted.

        _cleanup_expired() normally removes every expired entry before
        retrieve() re-checks the target key, so this branch only fires
        when an entry becomes stale between those two steps (e.g. a
        race). Simulate it by disabling cleanup and inserting an
        already-expired entry directly.
        """
        memory._cleanup_expired = lambda: None  # neutralize the earlier sweep
        memory._state.working_memory["stale"] = WorkingEntry(
            key="stale",
            value="ghost",
            agent_id="test_user",
            stashed_at=time.time() - 100,
            expires_at=time.time() - 50,
        )
        memory._dirty = False

        result = memory.retrieve("stale")

        assert result is None
        assert "stale" not in memory._state.working_memory
        assert memory._dirty is True

    # =========================================================================
    # get_recent_sessions()
    # =========================================================================

    def test_get_recent_sessions_empty_when_no_archives(self, memory):
        """No archived sessions yields an empty list."""
        assert memory.get_recent_sessions() == []

    def test_get_recent_sessions_reads_gzip_archive(self, memory):
        """A gzip-compressed archive is decoded and summarized."""
        state = SessionState.new("test_user")
        state.context["topic"] = "coverage"
        memory._archive_session(state)  # compression on by default

        sessions = memory.get_recent_sessions()

        assert len(sessions) == 1
        summary = sessions[0]
        assert summary["session_id"] == state.session_id
        assert summary["user_id"] == "test_user"
        assert "topic" in summary["context_keys"]
        assert summary["pattern_count"] == 0

    def test_get_recent_sessions_reads_plain_json_archive(self, memory):
        """An uncompressed archive (.json) is read via the plain-text path."""
        memory.config.archive_compression = False
        state = SessionState.new("test_user")
        memory._archive_session(state)

        sessions = memory.get_recent_sessions()

        assert len(sessions) == 1
        assert sessions[0]["session_id"] == state.session_id

    def test_get_recent_sessions_skips_corrupt_files(self, memory):
        """A corrupt archive file is logged and skipped, not raised."""
        good_state = SessionState.new("test_user")
        memory._archive_session(good_state)

        corrupt_file = memory.config.archive_dir / "session_corrupt.json"
        corrupt_file.write_text("{not valid json", encoding="utf-8")

        sessions = memory.get_recent_sessions()

        session_ids = [s["session_id"] for s in sessions]
        assert good_state.session_id in session_ids
        assert len(sessions) == 1

    def test_get_recent_sessions_respects_limit(self, memory):
        """Only `limit` most-recent sessions are returned."""
        import os

        for i in range(3):
            state = SessionState.new("test_user")
            state.session_id = f"session_ordered_{i}"
            path = memory._archive_session(state)
            # Force distinct mtimes so ordering is deterministic
            # regardless of filesystem timestamp resolution.
            os.utime(path, (time.time() + i, time.time() + i))

        sessions = memory.get_recent_sessions(limit=2)

        assert len(sessions) == 2
        # Most recent archive (highest mtime) first.
        assert sessions[0]["session_id"] == "session_ordered_2"
        assert sessions[1]["session_id"] == "session_ordered_1"

    # =========================================================================
    # Redis-compatibility no-ops
    # =========================================================================

    def test_use_mock_is_false(self, memory):
        """File-based memory reports use_mock is False."""
        assert memory.use_mock is False

    def test_publish_returns_zero(self, memory):
        """publish() is unsupported in file mode and returns 0."""
        assert memory.publish("some_channel", {"event": "test"}) == 0

    def test_subscribe_returns_false(self, memory):
        """subscribe() is unsupported in file mode and returns False."""
        assert memory.subscribe("some_channel", lambda msg: None) is False


class TestPatternStagingCoverageGaps:
    """Targeted tests for pattern-staging branches not exercised elsewhere.

    Covers: get_staged_patterns() type filtering, promote_pattern() for a
    missing pattern id and for an already-expired pattern, and
    _cleanup_expired_patterns() actually removing an expired pattern from
    state, disk, and marking the session dirty.
    """

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return str(tmp_path / "pattern_coverage_test")

    @pytest.fixture
    def memory(self, temp_storage):
        """Create FileSessionMemory instance."""
        config = FileSessionConfig(base_dir=temp_storage)
        mem = FileSessionMemory(user_id="test_user", config=config)
        yield mem
        mem.close()

    def test_get_staged_patterns_filtered_by_type(self, memory):
        """get_staged_patterns(pattern_type=...) returns only matching patterns."""
        memory.stage_pattern(
            pattern_id="sec_1",
            pattern_type="security",
            name="Security Pattern",
            description="desc",
        )
        memory.stage_pattern(
            pattern_id="perf_1",
            pattern_type="performance",
            name="Performance Pattern",
            description="desc",
        )

        security_only = memory.get_staged_patterns(pattern_type="security")

        assert len(security_only) == 1
        assert security_only[0].pattern_id == "sec_1"

    def test_promote_pattern_not_found(self, memory):
        """Promoting an unknown pattern id fails with 'Pattern not found'."""
        success, pattern, message = memory.promote_pattern("does_not_exist")

        assert success is False
        assert pattern is None
        assert message == "Pattern not found"

    def test_promote_pattern_expired_removes_it(self, memory):
        """Promoting an expired staged pattern removes it and reports expiry."""
        memory.stage_pattern(
            pattern_id="expired_pat",
            pattern_type="general",
            name="Expired Pattern",
            description="desc",
            confidence=0.9,
        )
        # Force expiry directly on the in-memory state.
        memory._state.staged_patterns["expired_pat"].expires_at = time.time() - 1

        success, pattern, message = memory.promote_pattern("expired_pat")

        assert success is False
        assert pattern is None
        assert message == "Pattern expired"
        assert "expired_pat" not in memory._state.staged_patterns

    def test_cleanup_expired_patterns_removes_state_and_file(self, memory):
        """An expired staged pattern is dropped from state, disk, and dirtied."""
        memory.stage_pattern(
            pattern_id="stale_pat",
            pattern_type="general",
            name="Stale Pattern",
            description="desc",
        )
        staged_file = memory.config.patterns_dir / "staged" / "stale_pat.json"
        assert staged_file.exists()

        memory._state.staged_patterns["stale_pat"].expires_at = time.time() - 1
        memory._dirty = False

        remaining = memory.get_staged_patterns()

        assert remaining == []
        assert "stale_pat" not in memory._state.staged_patterns
        assert not staged_file.exists()
        assert memory._dirty is True
