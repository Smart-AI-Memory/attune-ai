"""Locks must carry their TTL atomically, and readers must be bounded.

Library-review H2: every lock was taken with ``SETNX`` and then given a
TTL by a SECOND ``EXPIRE`` command. A crash in the window leaves the key
immortal with no reaper — for the background-service singleton that
means the service can never start again. The comment at that site read
"Use SETNX for atomic lock acquisition", which is the belief the class
falsifies: SETNX is atomic, SETNX-then-EXPIRE is not.

Library-review H5: recall readers on documented never-block paths built
clients with no ``socket_connect_timeout``, delegating the contract to
whichever redis-py is installed. On the declared pin floor (5.0.1) there
is no default and a blackholed endpoint blocks ~75s.

The lock tests run against a REAL Redis (skipped when none is reachable)
and read the TTL back off the server, because the defect is in what the
server ends up holding — a mock records the calls it was given, which is
precisely the thing that was already fine.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
import socket
import time
import uuid

import pytest

#: The suite scrubs REDIS_URL for hermeticity; the live lane takes its
#: endpoint from here.
LIVE_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/0")


@pytest.fixture()
def live_client():
    redis = pytest.importorskip("redis")
    client = redis.Redis.from_url(LIVE_REDIS_URL, socket_connect_timeout=0.5)
    try:
        client.ping()
    except Exception:  # noqa: BLE001 — any failure means "no server here"
        pytest.skip(f"no reachable Redis at {LIVE_REDIS_URL}")
    keys: list[str] = []
    yield client, keys
    for key in keys:
        client.delete(key)


class _MemoryStub:
    """Only the attribute the lock helpers read — not the lock itself."""

    def __init__(self, client):
        self._client = client


class _Recording:
    """A pass-through wrapper that records the commands it forwards.

    NOT a mock: every call reaches the real server and returns the real
    reply — the wrapper only notes what went past. That distinction is
    the point. Asserting the END STATE (a TTL is present) cannot tell
    the two implementations apart, because ``SETNX`` + ``EXPIRE`` leaves
    exactly the same TTL when nothing crashes, which is why this class
    survived review in the first place. Asserting that no ``EXPIRE`` was
    SENT while the key still came out with a TTL proves the TTL arrived
    with the ``SET``.

    An earlier version read the server's global ``commandstats``, which
    any unrelated client or concurrent test could perturb into a false
    failure (codex D11 lane, 2026-08-20). Per-client recording is
    deterministic and needs no exclusive server.
    """

    def __init__(self, client):
        self._client = client
        self.commands: list[str] = []

    def __getattr__(self, name):
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def _record(*args, **kwargs):
            self.commands.append(name)
            return attr(*args, **kwargs)

        return _record


def test_acquired_lock_carries_a_ttl_immediately(live_client):
    """Read the TTL off the SERVER — no second command may be required."""
    from attune.memory.cross_session.coordinator import CrossSessionCoordinator

    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    lock_key = f"empathy:lock:{resource}"
    keys.append(lock_key)

    recorder = _Recording(client)
    coordinator = CrossSessionCoordinator.__new__(CrossSessionCoordinator)
    coordinator._memory = _MemoryStub(recorder)
    coordinator._agent_id = "agent-1"

    assert coordinator.acquire_lock(resource, timeout_seconds=30) is True

    ttl = client.ttl(lock_key)
    assert ttl > 0, f"lock is immortal (TTL={ttl})"
    assert ttl <= 30
    assert (
        "expire" not in recorder.commands
    ), "the TTL came from a SECOND command — crash in between and it is immortal"


def test_second_acquirer_is_refused_while_the_lock_is_held(live_client):
    """Atomicity did not cost mutual exclusion."""
    from attune.memory.cross_session.coordinator import CrossSessionCoordinator

    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    keys.append(f"empathy:lock:{resource}")

    first = CrossSessionCoordinator.__new__(CrossSessionCoordinator)
    first._memory = _MemoryStub(client)
    first._agent_id = "agent-1"
    second = CrossSessionCoordinator.__new__(CrossSessionCoordinator)
    second._memory = _MemoryStub(client)
    second._agent_id = "agent-2"

    assert first.acquire_lock(resource, timeout_seconds=30) is True
    assert second.acquire_lock(resource, timeout_seconds=30) is False


def test_service_singleton_lock_carries_a_ttl_immediately(live_client):
    """The highest-consequence instance: no TTL here wedges the service."""
    from attune.memory.cross_session.models import KEY_SERVICE_LOCK
    from attune.memory.cross_session.service import BackgroundService

    client, keys = live_client
    client.delete(KEY_SERVICE_LOCK)
    keys.append(KEY_SERVICE_LOCK)

    recorder = _Recording(client)
    service = BackgroundService.__new__(BackgroundService)
    service._memory = _MemoryStub(recorder)

    assert service._acquire_service_lock() is True

    ttl = client.ttl(KEY_SERVICE_LOCK)
    assert ttl > 0, f"service lock is immortal (TTL={ttl})"
    assert (
        "expire" not in recorder.commands
    ), "a crash between SETNX and EXPIRE wedges the service permanently"


def test_conflict_lock_carries_a_ttl_immediately(live_client):
    """Third instance of the same class."""
    from attune.memory.cross_session.conflicts import resolve_first_write

    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    lock_key = f"empathy:lock:{resource}"
    keys.append(lock_key)

    recorder = _Recording(client)
    result = resolve_first_write(
        agent_id="agent-1", client=recorder, resource_key=resource, other_session=None
    )

    assert result.winner_agent_id == "agent-1"
    assert client.ttl(lock_key) > 0
    assert "expire" not in recorder.commands


# --------------------------------------------------------------------------
# H5 — the never-block contract, against a real unresponsive endpoint
# --------------------------------------------------------------------------


def test_recall_client_defaults_carry_explicit_timeouts():
    """The contract is stated here, not inherited from the installed redis-py."""
    pytest.importorskip("redis")
    from attune.memory.recall_redis import (
        DEFAULT_CONNECT_TIMEOUT,
        DEFAULT_SOCKET_TIMEOUT,
        connect_recall_redis,
    )

    kwargs = connect_recall_redis().connection_pool.connection_kwargs

    assert kwargs["socket_connect_timeout"] == DEFAULT_CONNECT_TIMEOUT
    assert kwargs["socket_timeout"] == DEFAULT_SOCKET_TIMEOUT


def test_a_caller_supplied_timeout_still_wins():
    """setdefault, not override — the tighter callers keep their bounds."""
    pytest.importorskip("redis")
    from attune.memory.recall_redis import connect_recall_redis

    kwargs = connect_recall_redis(socket_connect_timeout=0.25).connection_pool.connection_kwargs

    assert kwargs["socket_connect_timeout"] == 0.25


def test_the_factory_defaults_bound_an_unresponsive_endpoint():
    """A real hung endpoint, bounded by OUR defaults — not redis-py's.

    The endpoint is a real listening socket with a filled backlog: a
    blackholed host, not a closed port (which errors instantly and would
    prove nothing).

    No timeout is passed in, so what is under test is exactly the
    factory's own defaults. The bound asserted is well under the ~75s an
    unbounded client blocks for on the project's declared pin floor
    (redis 5.0.1, which supplies no default at all) and comfortably above
    the 2s connect + 5s read the factory sets — an earlier version passed
    an explicit 1s connect timeout and asserted ``elapsed < 15``, which a
    fallback to redis-py's own 5s read timeout would also satisfy, so it
    could not tell the two apart (codex D11 lane, 2026-08-20).
    """
    redis = pytest.importorskip("redis")
    from attune.memory.recall_redis import (
        DEFAULT_CONNECT_TIMEOUT,
        DEFAULT_SOCKET_TIMEOUT,
        connect_recall_redis,
    )

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(0)  # accept nothing; connections queue and stall
    port = listener.getsockname()[1]
    fillers = []
    for _ in range(3):
        filler = socket.socket()
        filler.setblocking(False)
        filler.connect_ex(("127.0.0.1", port))
        fillers.append(filler)

    client = connect_recall_redis(f"redis://127.0.0.1:{port}/0")
    started = time.monotonic()
    try:
        with pytest.raises(redis.RedisError):
            client.ping()
    finally:
        elapsed = time.monotonic() - started
        for filler in fillers:
            filler.close()
        listener.close()

    ceiling = DEFAULT_CONNECT_TIMEOUT + DEFAULT_SOCKET_TIMEOUT + 3
    assert elapsed < ceiling, (
        f"blocked {elapsed:.1f}s, over the {ceiling:.0f}s the factory's own "
        f"defaults allow — the never-block contract is not being set here"
    )
