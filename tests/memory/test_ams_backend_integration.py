"""Integration tests for AMSMemoryBackend against a REAL Agent Memory Server.

These exercise the two integration bugs that unit tests with a mocked
client could not catch (the backend was never run against a live
``agent-memory-client`` + server):

1. **Client construction** — ``agent-memory-client`` 0.14.0 takes
   ``MemoryAPIClient(MemoryClientConfig(base_url=...))``; the old
   ``MemoryAPIClient(base_url=...)`` call raised ``TypeError`` at
   instantiation, so the backend silently no-op'd.
2. **Event-loop lifecycle** — running each coroutine via a fresh
   ``asyncio.run`` closed the loop the persistent ``httpx.AsyncClient``
   was bound to, so the *second* call onward failed with
   ``RuntimeError: Event loop is closed``. The fix routes every
   coroutine through one persistent loop.

Prerequisites (skipped cleanly when absent):
    - ``agent-memory-client`` installed (the ``[redis]`` extra)
    - An Agent Memory Server reachable at ``AMS_BASE_URL``
      (default ``http://localhost:8000``)

Run locally with AMS up:
    pytest tests/memory/test_ams_backend_integration.py -v
"""

from __future__ import annotations

import os
import time
import urllib.request
import uuid

import pytest

pytest.importorskip("agent_memory_client")

_AMS_BASE_URL = os.environ.get("AMS_BASE_URL", "http://localhost:8000")


def _ams_running() -> bool:
    """True when an Agent Memory Server answers its health endpoint."""
    try:
        with urllib.request.urlopen(f"{_AMS_BASE_URL}/v1/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        # INTENTIONAL: any failure means "no server" -> skip integration tests.
        return False


pytestmark = pytest.mark.skipif(
    not _ams_running(),
    reason=f"No Agent Memory Server reachable at {_AMS_BASE_URL}",
)


@pytest.fixture
def backend():
    from attune_redis.config import RedisPluginConfig
    from attune_redis.memory import AMSMemoryBackend

    # Unique namespace per test run: the AMS store is persistent, so without
    # isolation, near-identical findings from prior runs make semantic recall
    # of *this* run's record non-deterministic.
    cfg = RedisPluginConfig(
        ams_base_url=_AMS_BASE_URL,
        ams_namespace=f"itest-{uuid.uuid4().hex[:12]}",
    )
    be = AMSMemoryBackend(cfg)
    yield be
    be.close()


def test_backend_instantiates_against_real_client():
    """Regression: client construction must not raise (bug #1).

    The old ``MemoryAPIClient(base_url=...)`` raised ``TypeError`` with
    client 0.14.0. Constructing the backend at all proves the fix.
    """
    from attune_redis.memory import AMSMemoryBackend

    be = AMSMemoryBackend()
    try:
        assert be.is_connected() is True
    finally:
        be.close()


def test_sequential_calls_survive_persistent_loop(backend):
    """Regression: two+ sequential calls must not hit a closed loop (bug #2).

    With the per-call ``asyncio.run`` wrapper, the first call closed the
    loop the httpx client was bound to and ``search`` (a later call)
    raised ``RuntimeError: Event loop is closed``. The persistent-loop
    wrapper keeps the client valid across calls.
    """
    sid = f"itest-{uuid.uuid4()}"
    # First call binds the client's connection pool to the persistent loop.
    assert backend.stash("probe-key", {"v": 1}, agent_id=sid) is True
    # Second call would have hit "Event loop is closed" pre-fix.
    results = backend.search("anything", limit=3)
    assert isinstance(results, list)
    # A third call on the same loop must also work.
    assert isinstance(backend.search("another query", limit=1), list)


def test_data_dict_round_trip(backend):
    """The key-value stash/retrieve path (working-memory data dict) works."""
    sid = f"itest-{uuid.uuid4()}"
    payload = {"score": 95, "note": "round-trip"}
    assert backend.stash("results", payload, agent_id=sid) is True
    got = backend.retrieve("results", agent_id=sid)
    assert got == payload


def test_remember_then_search_round_trip(backend):
    """D7: a remember() write is recallable via search() (Ollama-embedded)."""
    marker = f"itest-{uuid.uuid4().hex[:10]}"
    content = f"{marker}: integration finding for the searchable write path."
    assert (
        backend.remember(content, memory_id=marker, topics=["type:note", "cwd:/itest-proj"]) is True
    )

    # Embedding + indexing is server-side; allow a brief settle then search.
    # Query by the content text (self-similar embedding ranks the exact doc
    # highest) rather than the bare hex marker (semantically meaningless).
    hit = None
    for _ in range(10):
        results = backend.search(content, limit=10)
        hit = next((r for r in results if marker in (r.get("text") or "")), None)
        if hit is not None:
            break
        time.sleep(1)
    assert hit is not None, f"remember()'d content not found by search for {marker!r}"
    # cwd surfaced from topics -> recall_entries' cwd soft-sort works for AMS.
    assert hit["cwd"] == "/itest-proj"


def test_session_stash_round_trip():
    """D7 end-to-end: stash_entry -> recall_entries finds the finding.

    This is the round-trip that returned 0 hits before D7 (stash wrote the
    working-memory data dict; search reads long-term memory). With the
    remember()-based write path it must now be recallable.
    """
    from attune.memory.session_stash import (
        SessionStashEntry,
        recall_entries,
        stash_entry,
    )
    from attune_redis.config import RedisPluginConfig
    from attune_redis.memory import AMSMemoryBackend

    be = AMSMemoryBackend(
        RedisPluginConfig(
            ams_base_url=_AMS_BASE_URL,
            ams_namespace=f"itest-{uuid.uuid4().hex[:12]}",
        )
    )
    try:
        marker = f"itest-{uuid.uuid4().hex[:10]}"
        entry = SessionStashEntry.create(
            session_id=f"itest-{uuid.uuid4()}",
            cwd="/tmp/itest",
            type="decision",
            content=f"{marker}: end-to-end session-stash recall verification.",
        )
        assert stash_entry(entry, backend=be) is True
        # Query by the finding text (self-similar embedding ranks the exact
        # doc highest) rather than the bare hex marker.
        hit = None
        for _ in range(10):
            results = recall_entries(entry.content, top_k=10, backend=be)
            hit = next((r for r in results if marker in (r.get("text") or "")), None)
            if hit is not None:
                break
            time.sleep(1)
        assert hit is not None, f"stashed finding not recalled for {marker!r}"
    finally:
        be.close()


def _wait_until_searchable(backend, query, marker, timeout_s=30.0):
    """Poll ``backend``'s own namespace until ``marker`` is searchable.

    AMS indexes long-term memories on a background task, so a write is
    acknowledged before it is findable. The production readback is
    deliberately short (it runs inside a Stop hook), which makes it a
    poor gate for a test on a loaded runner — this polls to the
    property the test needs instead of to a latency budget.

    Uses ``time.monotonic`` so a wall-clock adjustment mid-poll cannot
    end the loop early or hang it.

    Returns:
        The matching record, or None if it never appeared.
    """
    deadline = time.monotonic() + timeout_s
    while True:
        for record in backend.search(query, limit=20):
            if marker in (record.get("text") or ""):
                return record
        if time.monotonic() >= deadline:
            return None
        time.sleep(1)


def test_search_is_namespace_isolated():
    """A namespace-scoped search must EXCLUDE other namespaces' records.

    The round-trip tests above prove PRESENCE ("the marker I wrote is
    findable"). They pass even if search leaks across namespaces, because a
    leak only *adds* results. This proves ISOLATION: write the *same* semantic
    content under two namespaces with distinct markers, then search from one
    and assert the other's marker is absent. If namespace scoping were ignored
    (search returning the whole store), the shared text would rank the other
    namespace's record highly and this would fail.
    """
    from attune_redis.config import RedisPluginConfig
    from attune_redis.memory import AMSMemoryBackend

    shared = "shared finding about redis namespace isolation in attune"
    marker_a = f"itest-{uuid.uuid4().hex[:10]}"
    marker_b = f"itest-{uuid.uuid4().hex[:10]}"

    be_a = AMSMemoryBackend(
        RedisPluginConfig(
            ams_base_url=_AMS_BASE_URL,
            ams_namespace=f"itest-A-{uuid.uuid4().hex[:8]}",
        )
    )
    be_b = AMSMemoryBackend(
        RedisPluginConfig(
            ams_base_url=_AMS_BASE_URL,
            ams_namespace=f"itest-B-{uuid.uuid4().hex[:8]}",
        )
    )
    try:
        # `remember` confirms with a readback bounded at ~6.3 s so it can run
        # inside a Stop hook; under a loaded parallel run AMS indexing can
        # exceed that and return False for a write that lands moments later.
        # The return value is kept for diagnosis, but searchability — polled
        # below — is what this test actually needs.
        ack_a = be_a.remember(f"{marker_a}: {shared}", memory_id=marker_a, topics=["type:note"])
        ack_b = be_b.remember(f"{marker_b}: {shared}", memory_id=marker_b, topics=["type:note"])

        # BOTH records must be searchable in their OWN namespace before the
        # isolation assertion means anything. Confirming only A would let a
        # never-indexed B pass vacuously: "B's marker is absent from A" is
        # trivially true when B was never written.
        hit_a = _wait_until_searchable(be_a, shared, marker_a)
        assert hit_a is not None, (
            f"A's own record not searchable from A for {marker_a!r} " f"(remember returned {ack_a})"
        )
        hit_b = _wait_until_searchable(be_b, shared, marker_b)
        assert hit_b is not None, (
            f"B's own record not searchable from B for {marker_b!r} "
            f"(remember returned {ack_b}) — without this the isolation "
            f"assertion below would pass vacuously"
        )

        # Isolation: B's marker must NOT surface in A's search, even though the
        # shared text would rank B's record highly if namespaces leaked.
        texts_a = " ".join(r.get("text") or "" for r in be_a.search(shared, limit=20))
        assert (
            marker_b not in texts_a
        ), "namespace leak: B's record surfaced in A's namespace-scoped search"
    finally:
        be_a.close()
        be_b.close()
