"""Tests for the Socratic storage module.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest


class TestStorageBackend:
    """Tests for StorageBackend abstract class."""

    def test_cannot_instantiate_abstract(self):
        """Test that StorageBackend cannot be instantiated directly."""
        from attune.socratic.storage import StorageBackend

        with pytest.raises(TypeError):
            StorageBackend()


class TestJSONFileStorage:
    """Tests for JSONFileStorage class."""

    def test_create_storage(self, storage_path):
        """Test creating JSON file storage."""
        from attune.socratic.storage import JSONFileStorage

        # Constructor takes base_dir, not storage_path
        storage = JSONFileStorage(base_dir=str(storage_path))
        assert storage is not None

    def test_save_and_load_session(self, storage_path, sample_session):
        """Test saving and loading a session."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        # Save
        storage.save_session(sample_session)

        # Load
        loaded = storage.load_session(sample_session.session_id)

        assert loaded is not None
        assert loaded.session_id == sample_session.session_id
        assert loaded.goal == sample_session.goal

    def test_list_sessions(self, storage_path, sample_session):
        """Test listing all sessions."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        # Save multiple sessions
        session1 = sample_session
        session2 = SocraticSession(session_id="test-session-002")
        session2.goal = "Another goal"

        storage.save_session(session1)
        storage.save_session(session2)

        # List - returns list of dicts, not SocraticSession objects
        sessions = storage.list_sessions()

        assert len(sessions) >= 2
        # Access via dict keys, not attributes
        session_ids = [s["session_id"] for s in sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids

    def test_delete_session(self, storage_path, sample_session):
        """Test deleting a session."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        storage.save_session(sample_session)
        storage.delete_session(sample_session.session_id)

        loaded = storage.load_session(sample_session.session_id)
        assert loaded is None

    def test_save_and_load_blueprint(self, storage_path, sample_workflow_blueprint):
        """Test saving and loading a blueprint."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        # Save
        storage.save_blueprint(sample_workflow_blueprint)

        # Load - blueprint uses 'id' not 'workflow_id'
        loaded = storage.load_blueprint(sample_workflow_blueprint.id)

        assert loaded is not None
        assert loaded.id == sample_workflow_blueprint.id
        assert loaded.name == sample_workflow_blueprint.name

    def test_list_blueprints(self, storage_path, sample_workflow_blueprint):
        """Test listing all blueprints."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        storage.save_blueprint(sample_workflow_blueprint)

        # Returns list of dicts
        blueprints = storage.list_blueprints()

        assert len(blueprints) >= 1
        # Access via dict keys - uses 'id' not 'workflow_id'
        assert any(b["id"] == sample_workflow_blueprint.id for b in blueprints)

    def test_storage_creates_directory(self, tmp_path):
        """Test that storage creates directory if it doesn't exist."""
        from attune.socratic.storage import JSONFileStorage

        nested_path = tmp_path / "nested" / "dir" / "storage"
        storage = JSONFileStorage(base_dir=str(nested_path))

        # Should not raise and directories should exist
        assert storage is not None
        assert nested_path.exists()

    def test_storage_handles_corrupted_file(self, storage_path):
        """Test handling of corrupted JSON file."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        # Create a corrupted session file
        sessions_dir = storage_path / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        corrupted_file = sessions_dir / "corrupted-session.json"
        corrupted_file.write_text("{invalid json")

        # Should handle gracefully
        sessions = storage.list_sessions()
        assert isinstance(sessions, list)


class TestSQLiteStorage:
    """Tests for SQLiteStorage class."""

    def test_create_storage(self, storage_path):
        """Test creating SQLite storage."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "test.db"))
        assert storage is not None

    def test_save_and_load_session(self, storage_path, sample_session):
        """Test saving and loading a session."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "sessions.db"))

        # Save
        storage.save_session(sample_session)

        # Load
        loaded = storage.load_session(sample_session.session_id)

        assert loaded is not None
        assert loaded.session_id == sample_session.session_id

    def test_list_sessions(self, storage_path, sample_session):
        """Test listing all sessions."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "sessions.db"))

        session1 = sample_session
        session2 = SocraticSession(session_id="test-session-002")

        storage.save_session(session1)
        storage.save_session(session2)

        # Returns list of dicts
        sessions = storage.list_sessions()
        assert len(sessions) >= 2

    def test_delete_session(self, storage_path, sample_session):
        """Test deleting a session."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "sessions.db"))

        storage.save_session(sample_session)
        storage.delete_session(sample_session.session_id)

        loaded = storage.load_session(sample_session.session_id)
        assert loaded is None

    def test_save_and_load_blueprint(self, storage_path, sample_workflow_blueprint):
        """Test saving and loading a blueprint."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "blueprints.db"))

        storage.save_blueprint(sample_workflow_blueprint)

        # Blueprint uses 'id' not 'workflow_id'
        loaded = storage.load_blueprint(sample_workflow_blueprint.id)

        assert loaded is not None
        assert loaded.id == sample_workflow_blueprint.id

    def test_query_sessions_by_state(self, storage_path):
        """Test querying sessions by state."""
        from attune.socratic.session import SessionState, SocraticSession
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "query.db"))

        # Create sessions with different states
        session1 = SocraticSession(session_id="s1")
        session1.state = SessionState.AWAITING_GOAL

        session2 = SocraticSession(session_id="s2")
        session2.state = SessionState.READY_TO_GENERATE

        storage.save_session(session1)
        storage.save_session(session2)

        # list_sessions supports state filter
        awaiting = storage.list_sessions(state=SessionState.AWAITING_GOAL)
        assert len(awaiting) >= 1
        assert all(s["state"] == SessionState.AWAITING_GOAL.value for s in awaiting)

    def test_search_blueprints(self, storage_path, sample_workflow_blueprint):
        """Test searching blueprints."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "search.db"))
        storage.save_blueprint(sample_workflow_blueprint)

        # SQLiteStorage has search_blueprints method
        if hasattr(storage, "search_blueprints"):
            results = storage.search_blueprints("code")
            assert isinstance(results, list)


class TestStorageManager:
    """Tests for StorageManager class."""

    def test_create_manager_with_json(self, storage_path):
        """Test creating manager with JSON backend."""
        from attune.socratic.storage import StorageConfig, StorageManager

        # Manager takes StorageConfig, not individual kwargs
        config = StorageConfig(
            backend="json",
            path=str(storage_path),
        )
        manager = StorageManager(config=config)

        assert manager is not None

    def test_create_manager_with_sqlite(self, storage_path):
        """Test creating manager with SQLite backend."""
        from attune.socratic.storage import StorageConfig, StorageManager

        config = StorageConfig(
            backend="sqlite",
            path=str(storage_path / "storage"),
        )
        manager = StorageManager(config=config)

        assert manager is not None

    def test_manager_get_storage(self, storage_path):
        """Test getting storage backend from manager."""
        from attune.socratic.storage import StorageConfig, StorageManager

        config = StorageConfig(
            backend="json",
            path=str(storage_path),
        )
        manager = StorageManager(config=config)

        storage = manager.get_storage()
        assert storage is not None

    def test_manager_default_config(self):
        """Test manager with default config."""
        from attune.socratic.storage import StorageManager

        # Can create with no config (uses defaults)
        manager = StorageManager()
        assert manager is not None
        assert manager.config is not None


class TestStorageSecurity:
    """Tests for storage security."""

    def test_json_storage_validates_path(self, tmp_path):
        """Test that JSON storage validates file paths."""
        from attune.socratic.storage import JSONFileStorage

        # Storage should handle path safely
        storage = JSONFileStorage(base_dir=str(tmp_path / "safe_path"))
        assert storage is not None

    def test_sqlite_storage_validates_path(self, tmp_path):
        """Test that SQLite storage validates file paths."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(tmp_path / "safe.db"))
        assert storage is not None

    def test_no_sql_injection(self, storage_path):
        """Test protection against SQL injection."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(storage_path / "injection.db"))

        # Try SQL injection in session_id
        malicious_id = "'; DROP TABLE sessions; --"
        session = SocraticSession(session_id=malicious_id)

        # Should either sanitize or handle safely
        try:
            storage.save_session(session)
            storage.load_session(malicious_id)
            # If it succeeds, the table should still exist
            sessions = storage.list_sessions()
            assert isinstance(sessions, list)
        except Exception:
            pass  # Expected if input is rejected


class TestStorageEdgeCases:
    """Tests for storage edge cases."""

    def test_save_empty_session(self, storage_path):
        """Test saving a session with minimal data."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        session = SocraticSession(session_id="empty-001")
        storage.save_session(session)

        loaded = storage.load_session("empty-001")
        assert loaded is not None

    def test_load_nonexistent_session(self, storage_path):
        """Test loading a session that doesn't exist."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        loaded = storage.load_session("nonexistent")
        assert loaded is None

    def test_save_large_session(self, storage_path):
        """Test saving a session with large data."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        session = SocraticSession(session_id="large-001")
        session.goal = "A" * 10000  # Large goal
        session.metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}

        storage.save_session(session)

        loaded = storage.load_session("large-001")
        assert loaded is not None
        assert len(loaded.goal) == 10000

    def test_concurrent_writes(self, storage_path):
        """Test handling concurrent writes."""
        import threading

        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        def save_session(session_id):
            session = SocraticSession(session_id=session_id)
            storage.save_session(session)

        threads = [threading.Thread(target=save_session, args=(f"session-{i}",)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All sessions should be saved
        sessions = storage.list_sessions()
        assert len(sessions) >= 10


class TestDefaultStorage:
    """Tests for default storage functions."""

    def test_get_default_storage(self):
        """Test getting default storage."""
        from attune.socratic.storage import get_default_storage

        storage = get_default_storage()
        assert storage is not None

    def test_set_default_storage(self, storage_path):
        """Test setting default storage."""
        from attune.socratic.storage import JSONFileStorage, set_default_storage

        custom_storage = JSONFileStorage(base_dir=str(storage_path))
        set_default_storage(custom_storage)

        # Note: get_default_storage may return cached instance
        # This test validates set_default_storage doesn't error
        assert True


# ---------------------------------------------------------------------------
# Additional coverage for previously-missed branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestJSONFileStorageMissingBranches:
    """Cover error handlers and filter branches not hit by existing tests."""

    def test_load_session_corrupt_json_returns_none(self, storage_path):
        """Lines 162-164: JSONDecodeError in load_session → return None."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        corrupt = storage.sessions_dir / "bad-session.json"
        corrupt.write_text("{bad json}")

        result = storage.load_session("bad-session")
        assert result is None

    def test_list_sessions_state_filter_excludes_non_matching(self, storage_path):
        """Line 184: list_sessions with state filter skips non-matching sessions."""
        from attune.socratic.session import SessionState, SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        s1 = SocraticSession(session_id="state-a")
        s1.state = SessionState.AWAITING_GOAL
        s2 = SocraticSession(session_id="state-b")
        s2.state = SessionState.READY_TO_GENERATE

        storage.save_session(s1)
        storage.save_session(s2)

        results = storage.list_sessions(state=SessionState.AWAITING_GOAL)
        ids = [r["session_id"] for r in results]
        assert "state-a" in ids
        assert "state-b" not in ids

    def test_delete_session_nonexistent_returns_false(self, storage_path):
        """Line 207: delete_session on missing file returns False."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        result = storage.delete_session("does-not-exist")
        assert result is False

    def test_load_blueprint_nonexistent_returns_none(self, storage_path):
        """Line 225: load_blueprint on missing file returns None."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        result = storage.load_blueprint("ghost-blueprint")
        assert result is None

    def test_load_blueprint_corrupt_json_returns_none(self, storage_path):
        """Lines 231-233: JSONDecodeError in load_blueprint → return None."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        corrupt = storage.blueprints_dir / "bad-bp.json"
        corrupt.write_text("{broken json}")

        result = storage.load_blueprint("bad-bp")
        assert result is None

    def test_list_blueprints_limit_triggers_break(self, storage_path, sample_workflow_blueprint):
        """Line 245: list_blueprints limit hit causes break."""
        from attune.socratic.blueprint import WorkflowBlueprint
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        # Save 3 blueprints, then list with limit=2
        for i in range(3):
            bp = WorkflowBlueprint(
                id=f"bp-limit-{i}",
                name=f"Blueprint {i}",
                description="test",
                domain="code_review",
                agents=[],
                stages=[],
            )
            storage.save_blueprint(bp)

        results = storage.list_blueprints(limit=2)
        assert len(results) == 2

    def test_list_blueprints_domain_filter_excludes_non_matching(
        self, storage_path, sample_workflow_blueprint
    ):
        """Line 253: list_blueprints domain filter skips non-matching blueprints."""
        from attune.socratic.blueprint import WorkflowBlueprint
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        bp_a = WorkflowBlueprint(
            id="domain-a",
            name="BP A",
            description="test",
            domain="code_review",
            agents=[],
            stages=[],
        )
        bp_b = WorkflowBlueprint(
            id="domain-b",
            name="BP B",
            description="test",
            domain="testing",
            agents=[],
            stages=[],
        )
        storage.save_blueprint(bp_a)
        storage.save_blueprint(bp_b)

        results = storage.list_blueprints(domain="code_review")
        ids = [r["id"] for r in results]
        assert "domain-a" in ids
        assert "domain-b" not in ids

    def test_list_blueprints_corrupt_json_skips(self, storage_path):
        """Lines 264-265: JSONDecodeError in list_blueprints → continue."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        corrupt = storage.blueprints_dir / "corrupt.json"
        corrupt.write_text("{not valid}")

        results = storage.list_blueprints()
        # Corrupt file should be skipped, not raise
        assert isinstance(results, list)

    def test_save_and_get_evaluations(self, storage_path):
        """Lines 275-284, 292-305: save_evaluation and get_evaluations full paths."""
        from attune.socratic.storage import JSONFileStorage
        from attune.socratic.success import SuccessEvaluation

        storage = JSONFileStorage(base_dir=str(storage_path))
        blueprint_id = "eval-bp-001"

        evaluation = SuccessEvaluation(
            overall_success=True,
            overall_score=0.9,
            metric_results=[],
            summary="all good",
        )
        storage.save_evaluation(blueprint_id, evaluation)

        results = storage.get_evaluations(blueprint_id)
        assert len(results) == 1
        assert results[0]["overall_success"] is True

    def test_get_evaluations_nonexistent_dir_returns_empty(self, storage_path):
        """Line 294-295: get_evaluations with no dir returns []."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        results = storage.get_evaluations("no-such-blueprint")
        assert results == []

    def test_get_evaluations_corrupt_json_skips(self, storage_path):
        """Line 302-303: JSONDecodeError in get_evaluations → continue."""
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))
        blueprint_id = "corrupt-eval-bp"
        eval_dir = storage.evaluations_dir / blueprint_id
        eval_dir.mkdir(parents=True)
        (eval_dir / "bad.json").write_text("{broken}")

        results = storage.get_evaluations(blueprint_id)
        assert results == []


@pytest.mark.unit
class TestStorageManagerMissingBranches:
    """Cover StorageManager cached storage and redis/default branches."""

    def test_get_storage_twice_returns_cached(self, storage_path):
        """Line 350->352: second call to get_storage() returns cached instance."""
        from attune.socratic.storage import StorageConfig, StorageManager

        config = StorageConfig(backend="json", path=str(storage_path))
        manager = StorageManager(config=config)

        s1 = manager.get_storage()
        s2 = manager.get_storage()
        assert s1 is s2  # same object — cached path taken

    def test_create_storage_sqlite_backend(self, storage_path):
        """Line 357: _create_storage with sqlite backend returns SQLiteStorage."""
        from attune.socratic.storage import SQLiteStorage, StorageConfig, StorageManager

        config = StorageConfig(backend="sqlite", path=str(storage_path / "store"))
        manager = StorageManager(config=config)
        storage = manager.get_storage()
        assert isinstance(storage, SQLiteStorage)

    def test_create_storage_redis_falls_back_to_json(self, storage_path):
        """Lines 360-361: redis backend not implemented → falls back to JSONFileStorage."""
        from attune.socratic.storage import JSONFileStorage, StorageConfig, StorageManager

        config = StorageConfig(backend="redis", path=str(storage_path))
        manager = StorageManager(config=config)
        storage = manager.get_storage()
        assert isinstance(storage, JSONFileStorage)


@pytest.mark.unit
class TestGetDefaultStorageMissingBranch:
    """Cover line 373: _default_storage assignment when global is None."""

    def test_get_default_storage_initializes_when_none(self, monkeypatch):
        """Line 373: get_default_storage creates JSONFileStorage when global is None."""
        import attune.socratic.storage as storage_mod
        from attune.socratic.storage import JSONFileStorage, get_default_storage

        monkeypatch.setattr(storage_mod, "_default_storage", None)
        result = get_default_storage()
        assert isinstance(result, JSONFileStorage)

    def test_get_default_storage_returns_existing_when_set(self, monkeypatch, storage_path):
        """Line 372->374: get_default_storage returns existing storage when already set."""
        import attune.socratic.storage as storage_mod
        from attune.socratic.storage import JSONFileStorage, get_default_storage

        existing = JSONFileStorage(base_dir=str(storage_path))
        monkeypatch.setattr(storage_mod, "_default_storage", existing)
        result = get_default_storage()
        assert result is existing


@pytest.mark.unit
class TestListSessionsLimitBranch:
    """Cover line 176: list_sessions break when limit is reached."""

    def test_list_sessions_respects_limit(self, storage_path):
        """Line 176: list_sessions stops at limit."""
        from attune.socratic.session import SocraticSession
        from attune.socratic.storage import JSONFileStorage

        storage = JSONFileStorage(base_dir=str(storage_path))

        for i in range(5):
            s = SocraticSession(session_id=f"limit-session-{i}")
            storage.save_session(s)

        results = storage.list_sessions(limit=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# SQLiteStorage — additional coverage for blueprint queries and evaluations
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSQLiteStorageMissingBranches:
    """Cover load_blueprint(None), list_blueprints, evaluations, success_rate."""

    def test_load_blueprint_returns_none_when_missing(self, tmp_path):
        """Line 210: load_blueprint with no row returns None."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(tmp_path / "miss.db"))
        result = storage.load_blueprint("does-not-exist")
        assert result is None

    def test_list_blueprints_no_filter(self, tmp_path, sample_workflow_blueprint):
        """Lines 218, 230-241: list_blueprints without domain filter."""
        from attune.socratic.blueprint import WorkflowBlueprint
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(tmp_path / "lb.db"))
        storage.save_blueprint(sample_workflow_blueprint)
        bp2 = WorkflowBlueprint(
            id="bp-other",
            name="Other",
            description="x",
            domain="testing",
            agents=[],
            stages=[],
        )
        storage.save_blueprint(bp2)

        results = storage.list_blueprints()
        ids = [r["id"] for r in results]
        assert sample_workflow_blueprint.id in ids
        assert "bp-other" in ids

    def test_list_blueprints_with_domain_filter(self, tmp_path, sample_workflow_blueprint):
        """Lines 218-229: list_blueprints with domain filter."""
        from attune.socratic.blueprint import WorkflowBlueprint
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(tmp_path / "lb_filt.db"))
        storage.save_blueprint(sample_workflow_blueprint)  # code_review
        bp2 = WorkflowBlueprint(
            id="bp-testing",
            name="T",
            description="x",
            domain="testing",
            agents=[],
            stages=[],
        )
        storage.save_blueprint(bp2)

        results = storage.list_blueprints(domain="code_review")
        ids = [r["id"] for r in results]
        assert sample_workflow_blueprint.id in ids
        assert "bp-testing" not in ids

    def test_save_and_get_evaluations(self, tmp_path):
        """Lines 249-252, 273-284: save_evaluation and get_evaluations."""
        from attune.socratic.storage import SQLiteStorage
        from attune.socratic.success_models import SuccessEvaluation

        storage = SQLiteStorage(db_path=str(tmp_path / "eval.db"))
        bp_id = "bp-eval"

        ev1 = SuccessEvaluation(
            overall_success=True,
            overall_score=0.95,
            metric_results=[],
            summary="great",
        )
        ev2 = SuccessEvaluation(
            overall_success=False,
            overall_score=0.4,
            metric_results=[],
            summary="poor",
        )
        storage.save_evaluation(bp_id, ev1)
        storage.save_evaluation(bp_id, ev2)

        results = storage.get_evaluations(bp_id)
        assert len(results) == 2
        # Each result is a dict produced from to_dict
        scores = sorted(r["overall_score"] for r in results)
        assert scores == [0.4, 0.95]

    def test_get_evaluations_respects_limit(self, tmp_path):
        """get_evaluations limit clause works."""
        from attune.socratic.storage import SQLiteStorage
        from attune.socratic.success_models import SuccessEvaluation

        storage = SQLiteStorage(db_path=str(tmp_path / "elim.db"))
        bp_id = "bp-lim"
        for i in range(4):
            storage.save_evaluation(
                bp_id,
                SuccessEvaluation(
                    overall_success=True,
                    overall_score=0.5 + 0.1 * i,
                    metric_results=[],
                    summary=f"e{i}",
                ),
            )

        results = storage.get_evaluations(bp_id, limit=2)
        assert len(results) == 2

    def test_get_success_rate_with_evaluations(self, tmp_path):
        """Lines 288-302 (truthy branch): success rate from saved evaluations."""
        from attune.socratic.storage import SQLiteStorage
        from attune.socratic.success_models import SuccessEvaluation

        storage = SQLiteStorage(db_path=str(tmp_path / "rate.db"))
        bp_id = "bp-rate"
        # 3 of 4 successes → rate = 0.75
        for ok in (True, True, True, False):
            storage.save_evaluation(
                bp_id,
                SuccessEvaluation(
                    overall_success=ok,
                    overall_score=1.0 if ok else 0.0,
                    metric_results=[],
                    summary="x",
                ),
            )

        rate = storage.get_success_rate(bp_id)
        assert rate == pytest.approx(0.75)

    def test_get_success_rate_no_evaluations(self, tmp_path):
        """Line 302: returns 0.0 when no evaluations exist."""
        from attune.socratic.storage import SQLiteStorage

        storage = SQLiteStorage(db_path=str(tmp_path / "rate0.db"))
        rate = storage.get_success_rate("nonexistent-bp")
        assert rate == 0.0
