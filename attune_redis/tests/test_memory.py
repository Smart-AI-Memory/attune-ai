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


class TestRetrieveMany:
    """Batched working-memory reads — one fetch serves every key."""

    def test_round_trip_many(self, backend):
        """Present keys map to values, missing keys to None."""
        backend.stash("a", 1)
        backend.stash("b", {"v": 2})
        got = backend.retrieve_many(["a", "b", "missing"])
        assert got == {"a": 1, "b": {"v": 2}, "missing": None}

    def test_single_fetch_for_many_keys(self, backend, mock_ams_client):
        """N keys cost exactly one working-memory fetch, not N."""
        backend.stash("a", 1)
        backend.stash("b", 2)
        mock_ams_client.get_or_create_working_memory.reset_mock()
        backend.retrieve_many(["a", "b"])
        assert mock_ams_client.get_or_create_working_memory.call_count == 1

    def test_empty_keys_skip_the_client(self, backend, mock_ams_client):
        """No keys, no round-trip."""
        mock_ams_client.get_or_create_working_memory.reset_mock()
        assert backend.retrieve_many([]) == {}
        mock_ams_client.get_or_create_working_memory.assert_not_called()

    def test_error_degrades_to_all_none(self, backend, mock_ams_client):
        """AMS errors map every key to None, matching retrieve()."""
        mock_ams_client.get_or_create_working_memory.side_effect = ConnectionError("down")
        assert backend.retrieve_many(["a", "b"]) == {"a": None, "b": None}


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


class TestWorkingMemoryReadIsNotDeprecated:
    """Reads use get_or_create_working_memory, not the deprecated
    get_working_memory (deprecated in agent-memory-client 0.14.0)."""

    def test_retrieve_uses_get_or_create(self, backend, mock_ams_client):
        """retrieve() reads via get_or_create_working_memory."""
        backend.retrieve("k")
        mock_ams_client.get_or_create_working_memory.assert_called()
        mock_ams_client.get_working_memory.assert_not_called()

    def test_delete_uses_get_or_create(self, backend, mock_ams_client):
        """delete() reads via get_or_create_working_memory."""
        backend.delete("k")
        mock_ams_client.get_or_create_working_memory.assert_called()
        mock_ams_client.get_working_memory.assert_not_called()

    def test_keys_uses_get_or_create(self, backend, mock_ams_client):
        """keys() reads via get_or_create_working_memory."""
        backend.keys()
        mock_ams_client.get_or_create_working_memory.assert_called()
        mock_ams_client.get_working_memory.assert_not_called()


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
# SearchableMemoryBackend: remember (searchable long-term write)
# =================================================================


def _last_record(mock_ams_client):
    """Return the single ClientMemoryRecord passed to the last
    create_long_term_memory call."""
    args, _ = mock_ams_client.create_long_term_memory.call_args
    return args[0][0]


class TestRemember:
    """Test searchable long-term writes and dedup-safe id derivation."""

    def test_remember_returns_true(self, backend):
        """remember() returns True on success."""
        assert backend.remember("a durable finding") is True

    def test_remember_derives_content_hash_id(self, backend, mock_ams_client):
        """remember() derives a stable sha256 id when none is supplied."""
        backend.remember("the event-loop reuse bug")
        rec = _last_record(mock_ams_client)
        assert rec.id.startswith("sha256-")

    def test_remember_distinct_content_distinct_ids(self, backend, mock_ams_client):
        """Different findings get different ids (so AMS won't merge them)."""
        backend.remember("alpha apple finding")
        id_a = _last_record(mock_ams_client).id
        backend.remember("beta banana finding")
        id_b = _last_record(mock_ams_client).id
        assert id_a != id_b

    def test_remember_identical_content_same_id(self, backend, mock_ams_client):
        """Identical content maps to the same id (upsert, not duplicate)."""
        backend.remember("repeated identical finding")
        id_1 = _last_record(mock_ams_client).id
        backend.remember("repeated identical finding")
        id_2 = _last_record(mock_ams_client).id
        assert id_1 == id_2

    def test_remember_explicit_id_wins(self, backend, mock_ams_client):
        """An explicit memory_id is used verbatim, not the derived hash."""
        backend.remember("some finding", memory_id="finding-42")
        assert _last_record(mock_ams_client).id == "finding-42"

    def test_remember_disables_semantic_dedup(self, backend, mock_ams_client):
        """remember() writes with deduplicate=False so distinct-but-similar
        findings are not silently merged (the stable id handles exact
        re-writes via upsert instead)."""
        backend.remember("a finding")
        _, kwargs = mock_ams_client.create_long_term_memory.call_args
        assert kwargs.get("deduplicate") is False

    def test_remember_carries_topics_and_session(self, backend, mock_ams_client):
        """remember() puts topics and session_id on the record."""
        backend.remember("x", session_id="s-7", topics=["cwd:/p", "type:insight"])
        rec = _last_record(mock_ams_client)
        assert rec.topics == ["cwd:/p", "type:insight"]
        assert rec.session_id == "s-7"

    def test_remember_returns_false_on_error(self, backend, mock_ams_client):
        """remember() degrades to False on AMS errors, never raises."""
        mock_ams_client.create_long_term_memory.side_effect = ConnectionError("boom")
        assert backend.remember("will fail") is False


# =================================================================
# SearchableMemoryBackend: search / promote
# =================================================================


class TestSearchable:
    """Test semantic search and promotion."""

    def test_search_returns_list(self, backend):
        """search() returns list of dicts."""
        results = backend.search("test query")
        assert isinstance(results, list)

    def test_search_clamps_limit_to_ams_cap(self, backend, mock_ams_client):
        """search() never passes a limit above AMS's hard cap of 100 (a
        larger value is a validation error that returns nothing)."""
        backend.search("q", limit=500)
        _, kwargs = mock_ams_client.search_long_term_memory.call_args
        assert kwargs["limit"] <= 100

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

    def test_recent_clamps_overscan_to_ams_cap(self, backend, mock_ams_client):
        """recent()'s over-fetch window never exceeds AMS's hard limit cap of
        100 — a larger value is a validation error that returns nothing."""
        backend.recent(limit=50)  # naive overscan would be 500
        _, kwargs = mock_ams_client.search_long_term_memory.call_args
        assert kwargs["limit"] <= 100

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
        """recent() returns the file-backend record shape (no score) plus the
        recency keys (``ts`` epoch float, ``created_at`` ISO) that promotion
        consumers order by — their absence was half of the 2026-07-04 R4 bug
        (every candidate surfaced with ``ts: None``)."""
        mock_ams_client.search_long_term_memory.return_value = FakeMemoryRecordResults(
            memories=[_rec("m1", "a finding", 5, topics=["cwd:/p", "tag"])]
        )
        out = backend.recent(limit=1)
        assert set(out[0].keys()) == {
            "id",
            "text",
            "topics",
            "cwd",
            "session_id",
            "ts",
            "created_at",
        }
        assert out[0]["cwd"] == "/p"
        assert out[0]["topics"] == ["cwd:/p", "tag"]
        assert isinstance(out[0]["ts"], float)
        assert out[0]["created_at"].startswith("2026-01-01")

    def test_recent_finds_fresh_records_in_large_namespace(self, backend, mock_ams_client):
        """Regression for the 2026-07-04 R4 failure: on a namespace larger
        than one 100-record page, the newest findings must still surface.

        The fake emulates the live AMS 0.14.0 behaviors that broke every
        naive listing (verified live): ``created_at`` range filters are
        honored, but any query matching >100 records is truncated to an
        ARBITRARY 100 — adversarially the oldest here, the selection that
        actually hid the fresh findings. Only a window-walk that bisects
        truncated windows recovers the true newest records."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        old_cluster = [
            FakeMemoryRecord(
                record_id=f"old-{i:03d}",
                text=f"aged finding {i}",
                created_at=now - timedelta(days=20) + timedelta(seconds=i * 144),
            )
            for i in range(150)  # spread over 6h, 20 days ago
        ]
        fresh = [
            FakeMemoryRecord(
                record_id=f"fresh-{i}",
                text=f"fresh finding {i}",
                created_at=now - timedelta(minutes=10 - i),
            )
            for i in range(5)
        ]
        corpus = old_cluster + fresh

        def _serve(**kwargs):
            matches = list(corpus)
            ca = kwargs.get("created_at")
            if ca is not None:
                matches = [
                    m
                    for m in matches
                    if (ca.gte is None or m.created_at >= ca.gte)
                    and (ca.lte is None or m.created_at <= ca.lte)
                ]
            # Adversarial truncation: oldest-first, as observed live.
            matches.sort(key=lambda m: m.created_at)
            return FakeMemoryRecordResults(memories=matches[: kwargs.get("limit", 10)])

        mock_ams_client.search_long_term_memory.side_effect = _serve
        out = backend.recent(limit=10)
        assert [d["id"] for d in out[:5]] == [
            "fresh-4",
            "fresh-3",
            "fresh-2",
            "fresh-1",
            "fresh-0",
        ], "the 5 fresh findings must lead, newest first"
        assert [d["id"] for d in out[5:]] == [
            "old-149",
            "old-148",
            "old-147",
            "old-146",
            "old-145",
        ], "then the newest of the aged cluster (lost to truncation pre-fix)"
        assert all(isinstance(d["ts"], float) for d in out), "ts populated on every record"

    def test_recent_request_cap_bounds_pathological_server(self, backend, mock_ams_client):
        """A server that returns a full page for EVERY window (ignoring the
        created_at filter) must not loop: the request cap terminates the walk
        and recent() still returns ``limit`` records."""
        full_page = FakeMemoryRecordResults(
            memories=[_rec(f"m-{i}", f"finding {i}", i) for i in range(100)]
        )
        mock_ams_client.search_long_term_memory.return_value = full_page
        out = backend.recent(limit=5)
        from attune_redis.memory import _RECENT_MAX_REQUESTS

        assert mock_ams_client.search_long_term_memory.call_count <= _RECENT_MAX_REQUESTS + 1
        assert len(out) == 5

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
