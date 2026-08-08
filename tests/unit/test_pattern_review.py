"""Tests for the pattern review queue (PatternReviewQueue).

Exercised against the real ``FileStashBackend`` (zero infra) so the
stage/list/promote/reject lifecycle round-trips through the actual backend
KV surface, and against a real in-memory ``PatternLibrary`` for promote.
"""

from __future__ import annotations

import pytest

from attune.memory.file_stash import FileStashBackend
from attune.memory.types import StagedPattern
from attune.pattern_library import Pattern, PatternLibrary
from attune.pattern_review import (
    ACTIVE_PREFIX,
    STAGED_PREFIX,
    PatternReviewQueue,
    PersistentPatternLibrary,
)


@pytest.fixture
def queue(tmp_path):
    return PatternReviewQueue(backend=FileStashBackend(base_dir=str(tmp_path)))


def _staged(
    pattern_id="p1",
    *,
    agent_id="a1",
    pattern_type="behavioral",
    confidence=0.8,
    name="n",
    code="x = 1",
):
    return StagedPattern(
        pattern_id=pattern_id,
        agent_id=agent_id,
        pattern_type=pattern_type,
        name=name,
        description="desc",
        code=code,
        confidence=confidence,
    )


class TestStageAndGet:
    def test_stage_then_get_round_trips(self, queue):
        assert queue.stage(_staged("p1", code="y = 2")) == "p1"
        got = queue.get("p1")
        assert got is not None
        assert got.pattern_id == "p1"
        assert got.code == "y = 2"
        assert got.confidence == 0.8

    def test_get_absent_returns_none(self, queue):
        assert queue.get("nope") is None

    def test_stage_same_id_overwrites(self, queue):
        queue.stage(_staged("p1", name="first"))
        queue.stage(_staged("p1", name="second"))
        assert queue.get("p1").name == "second"
        assert len(queue.list()) == 1


class TestList:
    def test_lists_sorted_by_confidence_desc(self, queue):
        queue.stage(_staged("low", confidence=0.2))
        queue.stage(_staged("high", confidence=0.9))
        queue.stage(_staged("mid", confidence=0.5))
        ids = [p.pattern_id for p in queue.list()]
        assert ids == ["high", "mid", "low"]

    def test_filter_by_type_agent_confidence(self, queue):
        queue.stage(_staged("a", pattern_type="behavioral", agent_id="x", confidence=0.9))
        queue.stage(_staged("b", pattern_type="temporal", agent_id="x", confidence=0.9))
        queue.stage(_staged("c", pattern_type="behavioral", agent_id="y", confidence=0.3))
        assert [p.pattern_id for p in queue.list(pattern_type="behavioral")] == ["a", "c"]
        assert [p.pattern_id for p in queue.list(agent_id="y")] == ["c"]
        assert [p.pattern_id for p in queue.list(min_confidence=0.5)] == ["a", "b"]

    def test_empty_queue_lists_nothing(self, queue):
        assert queue.list() == []

    def test_unparseable_entry_is_skipped(self, queue, tmp_path):
        queue.stage(_staged("good"))
        # Write a garbage value directly under the staged prefix.
        queue._backend.stash(STAGED_PREFIX + "bad", {"not": "a staged pattern"})
        ids = [p.pattern_id for p in queue.list()]
        assert ids == ["good"]


class TestPromote:
    def test_promote_contributes_and_drops_from_queue(self, queue):
        queue.stage(_staged("p1", agent_id="a1"))
        library = PatternLibrary()
        promoted = queue.promote("p1", library)
        assert isinstance(promoted, Pattern)
        assert promoted.id == "p1"
        assert "p1" in library.patterns
        assert queue.get("p1") is None  # dropped from the queue

    def test_promote_absent_returns_none(self, queue):
        assert queue.promote("nope", PatternLibrary()) is None

    def test_promote_duplicate_propagates_and_keeps_staged(self, queue):
        library = PatternLibrary()
        library.contribute_pattern(
            "a1",
            Pattern(
                id="p1", agent_id="a1", pattern_type="behavioral", name="existing", description="d"
            ),
        )
        queue.stage(_staged("p1"))
        with pytest.raises(ValueError):
            queue.promote("p1", library)
        # Stays staged so the reviewer can retry/reject.
        assert queue.get("p1") is not None


class TestReject:
    def test_reject_drops_and_returns_true(self, queue):
        queue.stage(_staged("p1"))
        assert queue.reject("p1", reason="noisy") is True
        assert queue.get("p1") is None

    def test_reject_absent_returns_false(self, queue):
        assert queue.reject("nope") is False


class TestPersistentLibrary:
    def test_contribute_persists_and_reloads(self, tmp_path):
        be = FileStashBackend(base_dir=str(tmp_path))
        lib = PersistentPatternLibrary(backend=be)
        lib.contribute_pattern(
            "a1",
            Pattern(id="p1", agent_id="a1", pattern_type="behavioral", name="n", description="d"),
        )
        # A fresh library over the same store reconstructs the pattern.
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        assert "p1" in reloaded.patterns
        assert reloaded.patterns["p1"].name == "n"

    def test_promote_into_persistent_library_is_durable(self, tmp_path):
        queue = PatternReviewQueue(backend=FileStashBackend(base_dir=str(tmp_path)))
        lib = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        queue.stage(_staged("p9", agent_id="a9"))
        queue.promote("p9", lib)
        # Survives in a brand-new library over the same backend; queue cleared.
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        assert "p9" in reloaded.patterns
        assert queue.get("p9") is None

    def test_record_outcome_persists_across_reload(self, tmp_path):
        # Regression: outcomes used to mutate only the in-memory Pattern, so
        # a reloaded library reset usage/success counts to zero.
        lib = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        lib.contribute_pattern(
            "a1",
            Pattern(id="p1", agent_id="a1", pattern_type="behavioral", name="n", description="d"),
        )
        lib.record_pattern_outcome("p1", success=True)
        lib.record_pattern_outcome("p1", success=False)
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        got = reloaded.patterns["p1"]
        assert got.usage_count == 2
        assert got.success_count == 1
        assert got.failure_count == 1

    def test_link_patterns_persists_graph_across_reload(self, tmp_path):
        # Regression: links used to live only in the in-memory pattern_graph.
        lib = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        for pid in ("p1", "p2"):
            lib.contribute_pattern(
                "a1",
                Pattern(
                    id=pid, agent_id="a1", pattern_type="behavioral", name="n", description="d"
                ),
            )
        lib.link_patterns("p1", "p2")
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        assert reloaded.pattern_graph["p1"] == ["p2"]
        assert reloaded.pattern_graph["p2"] == ["p1"]

    def test_load_drops_graph_edges_to_missing_patterns(self, tmp_path):
        be = FileStashBackend(base_dir=str(tmp_path))
        lib = PersistentPatternLibrary(backend=be)
        lib.contribute_pattern(
            "a1",
            Pattern(id="p1", agent_id="a1", pattern_type="behavioral", name="n", description="d"),
        )
        # Stored graph references a pattern that no longer exists in the store.
        be.stash("pattern_graph", {"p1": ["ghost"], "ghost": ["p1"]})
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        assert reloaded.pattern_graph["p1"] == []
        assert "ghost" not in reloaded.pattern_graph

    def test_record_outcome_absent_id_raises_and_persists_nothing(self, tmp_path):
        be = FileStashBackend(base_dir=str(tmp_path))
        lib = PersistentPatternLibrary(backend=be)
        with pytest.raises(ValueError):
            lib.record_pattern_outcome("ghost", success=True)
        assert be.retrieve(ACTIVE_PREFIX + "ghost") is None

    def test_load_skips_unparseable_active_entry(self, tmp_path):
        be = FileStashBackend(base_dir=str(tmp_path))
        lib = PersistentPatternLibrary(backend=be)
        lib.contribute_pattern(
            "a1",
            Pattern(id="good", agent_id="a1", pattern_type="behavioral", name="n", description="d"),
        )
        be.stash(ACTIVE_PREFIX + "bad", {"not": "a pattern"})
        reloaded = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        assert "good" in reloaded.patterns
        assert "bad" not in reloaded.patterns


class TestInternals:
    def test_default_backend_falls_back_to_file(self, monkeypatch):
        import attune.pattern_review as pr
        from attune.memory.file_stash import FileStashBackend

        monkeypatch.setattr("attune.memory.session_stash.resolve_backend", lambda b=None: None)
        assert isinstance(pr._default_backend(), FileStashBackend)

    def test_default_backend_prefers_resolved(self, monkeypatch):
        import attune.pattern_review as pr

        sentinel = object()
        monkeypatch.setattr("attune.memory.session_stash.resolve_backend", lambda b=None: sentinel)
        assert pr._default_backend() is sentinel

    def test_list_skips_falsy_value(self, queue):
        queue.stage(_staged("good"))
        queue._backend.stash(STAGED_PREFIX + "empty", None)
        assert [p.pattern_id for p in queue.list()] == ["good"]

    def test_list_skips_non_dict_value(self, queue):
        queue.stage(_staged("good"))
        queue._backend.stash(STAGED_PREFIX + "str", "not a dict at all")
        assert [p.pattern_id for p in queue.list()] == ["good"]

    def test_load_skips_non_dict_active_entry(self, tmp_path):
        be = FileStashBackend(base_dir=str(tmp_path))
        be.stash(ACTIVE_PREFIX + "weird", "not a dict")
        assert "weird" not in PersistentPatternLibrary(backend=be).patterns

    def test_load_skips_duplicate_active_id(self, tmp_path):
        import attune.pattern_review as pr

        be = FileStashBackend(base_dir=str(tmp_path))
        d = pr._pattern_to_dict(
            Pattern(id="dup", agent_id="a", pattern_type="behavioral", name="n", description="d")
        )
        be.stash(ACTIVE_PREFIX + "k1", d)
        be.stash(ACTIVE_PREFIX + "k2", d)  # same id under a second key
        lib = PersistentPatternLibrary(backend=be)
        assert "dup" in lib.patterns  # loaded once, dup skipped without error


class _NoBatchBackend:
    """Delegates to a real backend but HIDES ``retrieve_many``.

    Models a backend predating the batch extension, forcing
    ``_retrieve_all``'s per-key fallback; counts calls so tests can prove
    which path actually ran.
    """

    def __init__(self, inner):
        self._inner = inner
        self.retrieve_calls = 0

    def stash(self, key, value, ttl=None, agent_id=None):
        return self._inner.stash(key, value, ttl, agent_id)

    def retrieve(self, key, agent_id=None):
        self.retrieve_calls += 1
        return self._inner.retrieve(key, agent_id)

    def keys(self, pattern="*"):
        return self._inner.keys(pattern)

    def delete(self, key):
        return self._inner.delete(key)


class _CountingBatchBackend(_NoBatchBackend):
    """Delegating wrapper that also counts ``retrieve_many`` calls."""

    def __init__(self, inner):
        super().__init__(inner)
        self.retrieve_many_calls = 0

    def retrieve_many(self, keys, agent_id=None):
        self.retrieve_many_calls += 1
        return self._inner.retrieve_many(keys, agent_id)


class TestBatchRetrieve:
    """The batch (retrieve_many) and fallback (per-key) paths are equivalent."""

    def _seed(self, tmp_path, n=3):
        """Persist n patterns plus a graph edge into a tmp_path-backed store."""
        lib = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        for i in range(n):
            lib.contribute_pattern(
                "a1",
                Pattern(
                    id=f"p{i}",
                    agent_id="a1",
                    pattern_type="behavioral",
                    name=f"n{i}",
                    description="d",
                ),
            )
        lib.link_patterns("p0", "p1")

    def test_batch_and_fallback_load_identical_libraries(self, tmp_path):
        import attune.pattern_review as pr

        self._seed(tmp_path)
        batch_lib = PersistentPatternLibrary(backend=FileStashBackend(base_dir=str(tmp_path)))
        fallback_be = _NoBatchBackend(FileStashBackend(base_dir=str(tmp_path)))
        loop_lib = PersistentPatternLibrary(backend=fallback_be)
        assert fallback_be.retrieve_calls > 0  # the per-key path really ran
        assert set(batch_lib.patterns) == set(loop_lib.patterns) == {"p0", "p1", "p2"}
        for pid, pat in batch_lib.patterns.items():
            assert pr._pattern_to_dict(pat) == pr._pattern_to_dict(loop_lib.patterns[pid])
        assert batch_lib.pattern_graph == loop_lib.pattern_graph

    def test_load_uses_one_batch_call_not_per_key_retrieves(self, tmp_path):
        self._seed(tmp_path)
        be = _CountingBatchBackend(FileStashBackend(base_dir=str(tmp_path)))
        PersistentPatternLibrary(backend=be)
        assert be.retrieve_many_calls == 1  # all patterns in one round-trip
        assert be.retrieve_calls == 1  # only the single GRAPH_KEY read remains

    def test_queue_list_batch_and_fallback_agree(self, tmp_path):
        batch_q = PatternReviewQueue(
            backend=_CountingBatchBackend(FileStashBackend(base_dir=str(tmp_path)))
        )
        for i in range(3):
            batch_q.stage(_staged(f"s{i}", confidence=0.5 + i / 10))
        loop_q = PatternReviewQueue(
            backend=_NoBatchBackend(FileStashBackend(base_dir=str(tmp_path)))
        )
        batch_ids = [p.pattern_id for p in batch_q.list()]
        loop_ids = [p.pattern_id for p in loop_q.list()]
        assert batch_ids == loop_ids == ["s2", "s1", "s0"]  # confidence desc
        assert batch_q._backend.retrieve_many_calls == 1
        assert batch_q._backend.retrieve_calls == 0
        assert loop_q._backend.retrieve_calls == 3
