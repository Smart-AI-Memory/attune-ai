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
    from attune_redis.memory import AMSMemoryBackend

    be = AMSMemoryBackend()
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
