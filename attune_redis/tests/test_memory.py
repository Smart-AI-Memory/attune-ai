"""Tests for AMSMemoryBackend.

Uses mocked AMS client so no server is needed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.memory.backend import MemoryBackend, SearchableMemoryBackend
from attune_redis.memory import AMSMemoryBackend

from .conftest import (
    FakeMemoryRecord,
    FakeMemoryRecordResults,
)


@pytest.fixture()
def backend(redis_config, mock_ams_client):
    """Create an AMSMemoryBackend with mocked client."""
    with patch(
        "agent_memory_client.MemoryAPIClient",
        return_value=mock_ams_client,
    ):
        b = AMSMemoryBackend(config=redis_config)
        b._client = mock_ams_client
        return b


# =================================================================
# MemoryBackend protocol compliance
# =================================================================


class TestProtocolCompliance:
    """AMSMemoryBackend must satisfy MemoryBackend protocol."""

    def test_isinstance_check(self, backend):
        """Must pass runtime protocol check."""
        assert isinstance(backend, MemoryBackend)

    def test_searchable_isinstance_check(self, backend):
        """Must also satisfy SearchableMemoryBackend."""
        assert isinstance(backend, SearchableMemoryBackend)


# =================================================================
# stash / retrieve
# =================================================================


class TestStashRetrieve:
    """Test the core stash/retrieve cycle."""

    def test_stash_returns_true(self, backend):
        """stash() returns True on success."""
        assert backend.stash("k1", {"v": 1}) is True

    def test_retrieve_missing_returns_none(self, backend):
        """retrieve() returns None for missing keys."""
        assert backend.retrieve("missing") is None

    def test_round_trip(self, backend):
        """Stashed data is retrievable."""
        backend.stash("key", "value")
        assert backend.retrieve("key") == "value"

    def test_stash_multiple_keys(self, backend):
        """Multiple keys coexist."""
        backend.stash("a", 1)
        backend.stash("b", 2)
        assert backend.retrieve("a") == 1
        assert backend.retrieve("b") == 2

    def test_stash_overwrites(self, backend):
        """Stashing same key overwrites."""
        backend.stash("k", "old")
        backend.stash("k", "new")
        assert backend.retrieve("k") == "new"

    def test_stash_with_agent_id(self, backend, mock_ams_client):
        """agent_id maps to AMS session_id."""
        backend.stash("k", "v", agent_id="session-42")
        mock_ams_client.update_working_memory_data.assert_called_with(
            session_id="session-42",
            data_updates={"k": "v"},
            namespace="test",
            merge_strategy="merge",
        )


# =================================================================
# delete
# =================================================================


class TestDelete:
    """Test key deletion."""

    def test_delete_missing_returns_false(self, backend):
        """Deleting non-existent key returns False."""
        assert backend.delete("nope") is False

    def test_delete_existing_returns_true(self, backend):
        """Deleting existing key returns True."""
        backend.stash("k", "v")
        assert backend.delete("k") is True

    def test_delete_removes_key(self, backend):
        """Deleted key is no longer retrievable."""
        backend.stash("k", "v")
        backend.delete("k")
        assert backend.retrieve("k") is None


# =================================================================
# keys
# =================================================================


class TestKeys:
    """Test key listing with patterns."""

    def test_keys_all(self, backend):
        """keys('*') returns all keys."""
        backend.stash("a", 1)
        backend.stash("b", 2)
        result = backend.keys()
        assert set(result) == {"a", "b"}

    def test_keys_with_pattern(self, backend):
        """keys(pattern) filters correctly."""
        backend.stash("prefix:a", 1)
        backend.stash("prefix:b", 2)
        backend.stash("other", 3)
        result = backend.keys("prefix:*")
        assert set(result) == {"prefix:a", "prefix:b"}

    def test_keys_empty(self, backend):
        """keys() returns empty list when no data."""
        assert backend.keys() == []


# =================================================================
# is_connected / get_stats / close
# =================================================================


class TestLifecycle:
    """Test connection, stats, and cleanup."""

    def test_is_connected_when_healthy(self, backend):
        """is_connected() returns True when AMS responds."""
        assert backend.is_connected() is True

    def test_is_connected_when_down(self, backend, mock_ams_client):
        """is_connected() returns False on failure."""
        mock_ams_client.health_check.side_effect = ConnectionError
        assert backend.is_connected() is False

    def test_get_stats_returns_dict(self, backend):
        """get_stats() returns a dict with expected keys."""
        stats = backend.get_stats()
        assert isinstance(stats, dict)
        assert stats["mode"] == "ams"
        assert stats["connected"] is True

    def test_close_succeeds(self, backend, mock_ams_client):
        """close() calls client.close()."""
        backend.close()
        mock_ams_client.close.assert_called_once()

    def test_close_idempotent(self, backend, mock_ams_client):
        """close() can be called multiple times."""
        backend.close()
        backend.close()
        mock_ams_client.close.assert_called_once()

    def test_supports_distributed(self, backend):
        """AMS backend is always distributed."""
        assert backend.supports_distributed() is True

    def test_supports_realtime_without_redis(self, backend):
        """Realtime is False without redis_url."""
        assert backend.supports_realtime() is False

    def test_supports_realtime_with_redis(self, redis_config):
        """Realtime is True with redis_url."""
        redis_config.redis_url = "redis://localhost:6379"
        with patch("agent_memory_client.MemoryAPIClient"):
            b = AMSMemoryBackend(config=redis_config)
            assert b.supports_realtime() is True

    def test_context_manager(self, backend, mock_ams_client):
        """Works as context manager."""
        with backend:
            backend.stash("k", "v")
        mock_ams_client.close.assert_called_once()


# =================================================================
# SearchableMemoryBackend: search / promote
# =================================================================


class TestSearchable:
    """Test semantic search and promotion."""

    def test_search_returns_list(self, backend):
        """search() returns list of dicts."""
        results = backend.search("test query")
        assert isinstance(results, list)

    def test_search_maps_records(self, backend, mock_ams_client):
        """search() maps AMS records to dicts."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[
                FakeMemoryRecord(
                    record_id="m1",
                    text="found it",
                    topics=["auth"],
                ),
            ]
        )
        results = backend.search("auth bugs")
        assert len(results) == 1
        assert results[0]["id"] == "m1"
        assert results[0]["text"] == "found it"
        assert results[0]["topics"] == ["auth"]

    def test_promote_returns_true(self, backend):
        """promote() returns True on success."""
        assert backend.promote() is True

    def test_promote_with_session(self, backend, mock_ams_client):
        """promote() passes session_id to AMS."""
        backend.promote(session_id="s-42")
        mock_ams_client.promote_working_memories_to_long_term.assert_called_with(
            session_id="s-42",
            namespace="test",
        )


# =================================================================
# SearchableMemoryBackend: recent (query-less SessionStart recall)
# =================================================================


def _rec(record_id, text, ts, *, topics=None):
    """Build a FakeMemoryRecord with a created_at offset by ``ts`` seconds."""
    from datetime import datetime, timedelta, timezone

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return FakeMemoryRecord(
        record_id=record_id,
        text=text,
        topics=topics or [],
        created_at=base + timedelta(seconds=ts),
    )


class TestRecent:
    """Test query-less recency listing (powers SessionStart recall)."""

    def test_recent_empty_returns_empty_list(self, backend):
        """recent() returns [] when the namespace has no memories."""
        assert backend.recent() == []

    def test_recent_uses_empty_text_query(self, backend, mock_ams_client):
        """recent() issues an empty-text long-term search scoped to the namespace."""
        backend.recent(limit=3)
        _, kwargs = mock_ams_client.search_long_term_memory.call_args
        assert kwargs["text"] == ""
        assert kwargs["namespace"] == {"eq": "test"}
        # Over-fetches a bounded window (server can't recency-sort for us).
        assert kwargs["limit"] >= 3

    def test_recent_sorts_newest_first(self, backend, mock_ams_client):
        """recent() orders records by created_at descending, regardless of
        the order the server returned them in."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[
                _rec("old", "oldest", 0),
                _rec("new", "newest", 100),
                _rec("mid", "middle", 50),
            ]
        )
        out = backend.recent(limit=10)
        assert [d["text"] for d in out] == ["newest", "middle", "oldest"]

    def test_recent_cwd_soft_priority(self, backend, mock_ams_client):
        """recent(cwd=X) surfaces same-cwd findings first, recency preserved
        within each group."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[
                _rec("b-new", "beta newer", 100, topics=["cwd:/proj/beta"]),
                _rec("a-old", "alpha older", 10, topics=["cwd:/proj/alpha"]),
                _rec("a-new", "alpha newer", 90, topics=["cwd:/proj/alpha"]),
            ]
        )
        out = backend.recent(limit=10, cwd="/proj/alpha")
        # alpha group first (newer before older), then beta.
        assert [d["text"] for d in out] == ["alpha newer", "alpha older", "beta newer"]
        assert out[0]["cwd"] == "/proj/alpha"

    def test_recent_honors_limit(self, backend, mock_ams_client):
        """recent() truncates to ``limit`` after sorting."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[_rec(f"m{i}", f"finding {i}", i) for i in range(10)]
        )
        assert len(backend.recent(limit=2)) == 2

    def test_recent_maps_record_shape(self, backend, mock_ams_client):
        """recent() returns the file-backend record shape (no score)."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[_rec("m1", "a finding", 5, topics=["cwd:/p", "tag"])]
        )
        out = backend.recent(limit=1)
        assert set(out[0].keys()) == {"id", "text", "topics", "cwd", "session_id"}
        assert out[0]["cwd"] == "/p"
        assert out[0]["topics"] == ["cwd:/p", "tag"]

    def test_recent_handles_missing_created_at(self, backend, mock_ams_client):
        """recent() tolerates records with created_at=None (sorts them last)."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[
                FakeMemoryRecord(record_id="none", text="no-ts", created_at=None),
                _rec("dated", "dated", 50),
            ]
        )
        out = backend.recent(limit=10)
        assert [d["text"] for d in out] == ["dated", "no-ts"]

    def test_recent_returns_empty_on_error(self, backend, mock_ams_client):
        """recent() degrades gracefully to [] on AMS errors, never raises."""
        mock_ams_client.search_long_term_memory.side_effect = ConnectionError("boom")
        assert backend.recent() == []
