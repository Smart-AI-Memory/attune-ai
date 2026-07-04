"""Integration tests for AMSMemoryBackend.

These tests require a running Redis Agent Memory Server.
They skip automatically when AMS is unavailable.

Run with:
    pytest attune_redis/tests/test_integration.py -v -m integration

Start AMS locally:
    docker run -d -p 8000:8000 redis/agent-memory-server
"""

from __future__ import annotations

import os
import uuid

import pytest

from attune_redis.config import RedisPluginConfig

# All tests in this module require a live AMS instance
pytestmark = [pytest.mark.integration]


def _ams_available() -> bool:
    """Check if AMS is reachable."""
    try:
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
        )
        backend = AMSMemoryBackend(config=config)
        connected = backend.is_connected()
        backend.close()
        return connected
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Any failure means AMS is unavailable
        return False


# Skip entire module if AMS is not running
pytestmark.append(
    pytest.mark.skipif(
        not _ams_available(),
        reason="AMS not available (set AMS_BASE_URL or run locally)",
    )
)


@pytest.fixture()
def backend():
    """Create AMSMemoryBackend connected to live AMS."""
    from attune_redis.memory import AMSMemoryBackend

    session_id = f"integration-test-{uuid.uuid4().hex[:8]}"
    config = RedisPluginConfig(
        ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
        ams_namespace="attune-test",
        default_session_id=session_id,
    )
    b = AMSMemoryBackend(config=config)
    yield b
    b.close()


class TestStashRetrieveRoundTrip:
    """Test real stash/retrieve against AMS."""

    def test_stash_returns_true(self, backend):
        """stash() succeeds against live AMS."""
        assert backend.stash("test-key", {"hello": "world"}) is True

    def test_retrieve_after_stash(self, backend):
        """retrieve() returns what was stashed."""
        backend.stash("round-trip", "test-value")
        result = backend.retrieve("round-trip")
        assert result == "test-value"

    def test_retrieve_missing_returns_none(self, backend):
        """retrieve() returns None for missing keys."""
        result = backend.retrieve("nonexistent-key")
        assert result is None

    def test_stash_complex_data(self, backend):
        """stash() handles nested dicts and lists."""
        data = {
            "scores": [1, 2, 3],
            "nested": {"a": True, "b": None},
        }
        backend.stash("complex", data)
        result = backend.retrieve("complex")
        assert result == data

    def test_second_stash_preserves_first_key(self, backend):
        """A second stash must not clobber the first key.

        Regression guard: AMS 0.14.0's set_working_memory_data REPLACES the
        whole data dict (preserve_existing only preserves messages/memories),
        so the prior stash(...) over set_working_memory_data wiped earlier
        keys — breaking multi-key retrieve and keys(). stash() now merges via
        update_working_memory_data(merge_strategy="merge").
        """
        backend.stash("first", "one")
        backend.stash("second", "two")
        assert backend.retrieve("first") == "one"
        assert backend.retrieve("second") == "two"


class TestDelete:
    """Test real delete against AMS."""

    def test_delete_existing(self, backend):
        """delete() returns True for existing key."""
        backend.stash("to-delete", "value")
        assert backend.delete("to-delete") is True

    def test_delete_missing(self, backend):
        """delete() returns False for missing key."""
        assert backend.delete("never-existed") is False

    def test_delete_removes_key(self, backend):
        """deleted key is no longer retrievable."""
        backend.stash("temp", "data")
        backend.delete("temp")
        assert backend.retrieve("temp") is None


class TestKeys:
    """Test real keys listing against AMS."""

    def test_keys_returns_stashed_keys(self, backend):
        """keys() includes recently stashed keys."""
        backend.stash("k1", 1)
        backend.stash("k2", 2)
        result = backend.keys()
        assert "k1" in result
        assert "k2" in result

    def test_keys_with_pattern(self, backend):
        """keys() filters by glob pattern."""
        backend.stash("prefix:a", 1)
        backend.stash("prefix:b", 2)
        backend.stash("other", 3)
        result = backend.keys("prefix:*")
        assert "prefix:a" in result
        assert "prefix:b" in result
        assert "other" not in result


class TestConnectionLifecycle:
    """Test connection health and lifecycle."""

    def test_is_connected(self, backend):
        """is_connected() returns True when AMS is up."""
        assert backend.is_connected() is True

    def test_get_stats(self, backend):
        """get_stats() returns dict with connection info."""
        stats = backend.get_stats()
        assert isinstance(stats, dict)
        assert stats["mode"] == "ams"
        assert stats["connected"] is True

    def test_close_and_reconnect(self):
        """close() doesn't prevent creating a new backend."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
            ams_namespace="attune-test",
            default_session_id=f"lifecycle-{uuid.uuid4().hex[:8]}",
        )
        b1 = AMSMemoryBackend(config=config)
        b1.stash("before-close", "value")
        b1.close()

        b2 = AMSMemoryBackend(config=config)
        assert b2.is_connected() is True
        b2.close()


class TestRecentLongTerm:
    """Test query-less recency listing against live AMS (SessionStart recall)."""

    def test_recent_newest_first_with_cwd_priority(self):
        """recent() returns long-term findings newest-first, cwd-prioritized.

        Uses a per-run namespace for isolation (a persistent semantic store
        accumulates across runs) and polls for eventual indexing. Findings
        are phrased distinctly to avoid AMS's semantic dedup on write.
        """
        import time

        from attune_redis.memory import AMSMemoryBackend

        ns = f"recent-itest-{uuid.uuid4().hex[:8]}"
        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
            ams_namespace=ns,
        )
        b = AMSMemoryBackend(config=config)
        try:
            findings = [
                ("Repaired the event-loop reuse defect in the wrapper", "/proj/alpha"),
                ("Switched the corpus loader to direct filesystem reads", "/proj/beta"),
                ("Wired int8 vector quantization through the factory seam", "/proj/alpha"),
                ("Observed server ordering is relevance rather than recency", "/proj/beta"),
            ]
            for text, cwd in findings:
                assert b.remember(text, topics=[f"cwd:{cwd}"]) is True
                time.sleep(0.5)

            # Eventual indexing: poll until all four are visible.
            out: list = []
            for _ in range(20):
                time.sleep(1.0)
                out = b.recent(limit=10)
                if len(out) >= 4:
                    break
            assert len(out) >= 4, f"only {len(out)} findings indexed"

            # Newest-first: the last-written finding leads.
            assert out[0]["text"].startswith("Observed server ordering")

            # Soft cwd priority: same-project findings surface first.
            out_alpha = b.recent(limit=10, cwd="/proj/alpha")
            assert out_alpha[0]["cwd"] == "/proj/alpha"
            assert out_alpha[1]["cwd"] == "/proj/alpha"

            # File-backend record shape (no score) plus the recency keys.
            assert set(out[0].keys()) == {
                "id",
                "text",
                "topics",
                "cwd",
                "session_id",
                "ts",
                "created_at",
            }
            assert isinstance(out[0]["ts"], float), "ts must carry the created_at epoch"

            # Limit honored.
            assert len(b.recent(limit=2)) == 2
        finally:
            b.close()

    def test_recent_surfaces_fresh_finding_in_large_namespace(self):
        """Regression for the 2026-07-04 R4 promotion failure: a namespace
        holding more records than one AMS search page (100) must still
        surface a just-written finding, newest-first with populated ``ts``.

        The old single-page recent() asked the server for one relevance-
        ordered page; fresh findings outside that page were unrecoverable.
        This seeds 110 backdated records through the raw client (one batched
        write), then stashes one fresh finding via remember() and requires it
        to lead recent().
        """
        import time
        from datetime import datetime, timedelta, timezone

        from agent_memory_client.models import ClientMemoryRecord

        from attune_redis.memory import AMSMemoryBackend, _run_sync

        ns = f"recent-page-itest-{uuid.uuid4().hex[:8]}"
        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
            ams_namespace=ns,
        )
        with AMSMemoryBackend(config=config) as b:
            backdated = datetime.now(timezone.utc) - timedelta(days=20)
            seeds = [
                ClientMemoryRecord(
                    id=f"seed-{i:03d}",
                    text=f"aged seed finding number {i} with distinct token tk{i}",
                    namespace=ns,
                    created_at=backdated + timedelta(seconds=i),
                    topics=["cwd:/proj/seeded"],
                )
                for i in range(110)
            ]
            _run_sync(b._client.create_long_term_memory(seeds, deduplicate=False))

            # Wait for the seeds to index before writing the fresh finding.
            for _ in range(30):
                time.sleep(1.0)
                if len(b.recent(limit=100)) >= 100:
                    break

            assert b.remember(
                "the freshly stashed finding that must win recency",
                topics=["cwd:/proj/fresh"],
            )

            out: list = []
            for _ in range(20):
                time.sleep(1.0)
                out = b.recent(limit=10)
                if out and out[0]["text"].startswith("the freshly stashed"):
                    break
            assert out, "recent() returned nothing"
            assert out[0]["text"].startswith(
                "the freshly stashed"
            ), f"fresh finding lost to aged seeds; got {out[0]['text']!r}"
            assert isinstance(out[0]["ts"], float)
            # cwd scoping must not go stale either: scoping to the fresh
            # finding's project surfaces it even among 110 other-cwd records.
            scoped = b.recent(limit=5, cwd="/proj/fresh")
            assert scoped and scoped[0]["cwd"] == "/proj/fresh"


class TestRememberDedup:
    """Live guard for the dedup-safe id derivation in remember()."""

    def _backend(self, ns: str):
        from attune_redis.memory import AMSMemoryBackend

        return AMSMemoryBackend(
            config=RedisPluginConfig(
                ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
                ams_namespace=ns,
            )
        )

    def test_similar_findings_all_survive_without_explicit_id(self):
        """Distinct-but-similar findings written via id-less remember() must
        all persist — AMS's default semantic dedup would otherwise merge
        near-in-embedding-space records (regression guard for the #660
        finding)."""
        import time

        ns = f"dedup-itest-{uuid.uuid4().hex[:8]}"
        b = self._backend(ns)
        try:
            similar = [
                "alpha apple finding",
                "beta banana finding",
                "gamma grape finding",
            ]
            for text in similar:
                assert b.remember(text) is True  # no explicit memory_id
                time.sleep(0.5)
            # Count via the query-less recall path (empty-text search returns
            # the namespace's records); semantic search applies a relevance
            # cutoff and is not a reliable count.
            total = 0
            for _ in range(20):
                time.sleep(1.0)
                total = len(b.recent(limit=50))
                if total >= 3:
                    break
            assert total >= 3, f"only {total}/3 similar findings survived (semantic merge)"
        finally:
            b.close()

    def test_identical_content_upserts(self):
        """Re-writing identical content maps to the same derived id, so it
        upserts rather than accumulating duplicates."""
        import time

        ns = f"upsert-itest-{uuid.uuid4().hex[:8]}"
        b = self._backend(ns)
        try:
            for _ in range(3):
                assert b.remember("one repeated identical finding") is True
                time.sleep(0.5)
            time.sleep(3.0)
            results = b.recent(limit=50)
            assert len(results) == 1, f"expected 1 upserted record, got {len(results)}"
        finally:
            b.close()


class TestErrorHandling:
    """Test graceful degradation with bad config."""

    def test_bad_url_stash_returns_false(self):
        """stash() returns False when AMS is unreachable."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url="http://localhost:19999",
            default_session_id="error-test",
        )
        b = AMSMemoryBackend(config=config)
        assert b.stash("key", "val") is False
        b.close()

    def test_bad_url_is_connected_returns_false(self):
        """is_connected() returns False for bad URL."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url="http://localhost:19999",
            default_session_id="error-test",
        )
        b = AMSMemoryBackend(config=config)
        assert b.is_connected() is False
        b.close()
