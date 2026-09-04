"""Releasing a lock must prove ownership and delete in ONE operation.

Library-review class **H6** — sibling of H2, on the other half of the
lock's life. H2 fixed ACQUISITION (``SETNX`` + ``EXPIRE`` -> ``SET``
nx+ex). RELEASE was left as check-then-act across two round trips::

    current_owner = client.get(lock_key)     # read
    if current_owner == self._agent_id:
        client.delete(lock_key)              # delete, unconditional

Locks carry a TTL (``acquire_lock`` defaults to 300s), so the key CAN
vanish between those two commands. The dangerous interleaving:

1. A's GET returns A's own id — the lock is genuinely still A's
2. A's lock expires
3. B acquires the now-free lock
4. A's DELETE fires and removes **B's** lock
5. C acquires while B still believes it holds it — two writers

The window is narrow but reachable under a GC pause, a slow network
hop, or a descheduled thread. This is exactly why the Redis
distributed-lock guidance mandates a Lua compare-and-delete for
release rather than GET-then-DEL.

**Why these tests use a real server, and why they control the
scheduling.** Per the class-M ruling, a test may not stand in for the
boundary its fix is about — and the boundary here IS the pair of real
round trips. A mock records the calls it was handed, which was never
the broken part. So every command below reaches a real ``redis-server``
and returns its real reply; the only thing the wrapper does is decide
*when* the world moves, making deterministic what a GC pause would
otherwise do at random.

**Why an end-state assertion cannot see this class** (the H2 lesson,
restated one layer over): "after a non-owner release, the owner's lock
survives" passes against the BROKEN code, because a non-owner's GET
returns someone else's id and the broken branch correctly declines to
delete. The defect only exists *inside* the window, so the test has to
open the window.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import os
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
    """Pass-through wrapper that notes which commands it forwarded.

    NOT a mock: every call reaches the real server and returns the real
    reply. Per-client recording (rather than the server's global
    ``commandstats``) keeps the assertion deterministic when other
    clients share the server.
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


class _InterleaveAfterFirstCommand:
    """Pass-through wrapper that moves the world once, mid-operation.

    Starts DISARMED and must be armed explicitly, so the hook lands
    inside the operation under test rather than inside whatever setup
    ran first. (The first version of this test armed on construction,
    so the hook fired after ``acquire_lock``'s ``SET``; the lock then
    changed hands BEFORE the release began, the broken code's ``GET``
    duly returned someone else's id, and the test passed against the
    defect it exists to catch — the class-M trap, on my own test.)

    Once armed, the hook fires immediately AFTER the first forwarded
    command's real reply comes back, and never again. That is precisely
    the check-then-act window: pre-fix the first command of a release is
    the ``GET``, so the hook lands between the read and the delete.
    Post-fix the first command is the ``EVAL``, which has already
    completed atomically on the server — there is no window left to land
    in, which is the whole property under test.
    """

    def __init__(self, client, hook):
        self._client = client
        self._hook = hook
        self.commands: list[str] = []
        self._armed = False

    def arm(self):
        self._armed = True

    def __getattr__(self, name):
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def _forward(*args, **kwargs):
            self.commands.append(name)
            reply = attr(*args, **kwargs)
            if self._armed:
                self._armed = False
                self._hook()
            return reply

        return _forward


def _coordinator(client, agent_id):
    from attune.memory.cross_session.coordinator import CrossSessionCoordinator

    coordinator = CrossSessionCoordinator.__new__(CrossSessionCoordinator)
    coordinator._memory = _MemoryStub(client)
    coordinator._agent_id = agent_id
    return coordinator


def _text(value):
    return value.decode() if isinstance(value, bytes) else value


# --------------------------------------------------------------------------
# The class itself — a real expiry inside the check-then-act window
# --------------------------------------------------------------------------


def test_a_lock_expiring_mid_release_does_not_clobber_the_next_owner(live_client):
    """A releases; its lock really expires mid-flight; B must survive.

    The expiry is a REAL server-side expiry (a 1s TTL, waited out), not
    a simulated delete — the point is that the key vanishes by the same
    mechanism production uses.
    """
    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    lock_key = f"empathy:lock:{resource}"
    keys.append(lock_key)

    agent_b = _coordinator(client, "agent-b")

    def steal_the_lock():
        """A's lock expires for real, then B takes the freed lock."""
        deadline = time.monotonic() + 5
        while client.exists(lock_key) and time.monotonic() < deadline:
            time.sleep(0.02)
        assert not client.exists(lock_key), "A's 1s lock never expired"
        assert agent_b.acquire_lock(resource, timeout_seconds=30) is True

    interleaver = _InterleaveAfterFirstCommand(client, steal_the_lock)
    agent_a = _coordinator(interleaver, "agent-a")

    assert agent_a.acquire_lock(resource, timeout_seconds=1) is True
    interleaver.arm()  # the window under test is the RELEASE, not the acquire
    agent_a.release_lock(resource)

    assert _text(client.get(lock_key)) == "agent-b", (
        "A's release deleted B's lock — the key expired between A's GET and "
        "A's DELETE, so the unconditional delete removed a lock A did not own"
    )


def test_release_sends_no_separate_read(live_client):
    """The mechanism, observed directly: compare and delete are one command.

    A round-trip count is what distinguishes atomic from non-atomic here;
    the end state after an uncontended release is identical either way.
    """
    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    lock_key = f"empathy:lock:{resource}"
    keys.append(lock_key)

    recorder = _Recording(client)
    coordinator = _coordinator(recorder, "agent-a")

    assert coordinator.acquire_lock(resource, timeout_seconds=30) is True
    recorder.commands.clear()

    assert coordinator.release_lock(resource) is True

    assert recorder.commands == ["eval"], (
        f"release issued {recorder.commands} — a read followed by a delete "
        f"leaves a window in which the lock can change hands"
    )
    assert not client.exists(lock_key)


# --------------------------------------------------------------------------
# The contract release_lock already had, preserved
# --------------------------------------------------------------------------


def test_a_non_owner_release_returns_false_and_leaves_the_lock(live_client):
    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    lock_key = f"empathy:lock:{resource}"
    keys.append(lock_key)

    assert _coordinator(client, "agent-a").acquire_lock(resource, timeout_seconds=30) is True

    assert _coordinator(client, "agent-b").release_lock(resource) is False
    assert _text(client.get(lock_key)) == "agent-a"


def test_releasing_an_absent_lock_returns_false(live_client):
    client, keys = live_client
    resource = f"res-{uuid.uuid4().hex[:8]}"
    keys.append(f"empathy:lock:{resource}")

    assert _coordinator(client, "agent-a").release_lock(resource) is False


def test_release_without_a_client_returns_false():
    """Degrade, never raise, when the memory layer is absent."""
    assert _coordinator(None, "agent-a").release_lock("anything") is False


def test_refresh_without_a_client_returns_false():
    """Same degrade contract on the refresh half: no client, no extension."""
    from attune.memory.cross_session.locks import refresh_if_owner

    assert refresh_if_owner(None, "any:lock", "agent-a", 30) is False


# --------------------------------------------------------------------------
# Sweep — the same class on the service singleton lock
# --------------------------------------------------------------------------


def _service(client):
    from attune.memory.cross_session.service import BackgroundService

    service = BackgroundService.__new__(BackgroundService)
    service._memory = _MemoryStub(client)
    return service


def test_service_release_does_not_delete_another_processs_lock(live_client):
    """``_release_service_lock`` deleted the key with no ownership check at all.

    A service whose lock lapsed (a stop that outlived the 60s TTL) would,
    on its way out, delete the lock a DIFFERENT live service had since
    taken — and a third would then start alongside it. The singleton
    guarantee is the entire purpose of this key.
    """
    from attune.memory.cross_session.models import KEY_SERVICE_LOCK

    client, keys = live_client
    keys.append(KEY_SERVICE_LOCK)
    client.delete(KEY_SERVICE_LOCK)

    other_pid = os.getpid() + 1
    client.set(KEY_SERVICE_LOCK, other_pid, ex=60)

    _service(client)._release_service_lock()

    assert _text(client.get(KEY_SERVICE_LOCK)) == str(
        other_pid
    ), "a stopping service deleted the singleton lock held by a live one"


def test_service_release_still_releases_its_own_lock(live_client):
    from attune.memory.cross_session.models import KEY_SERVICE_LOCK

    client, keys = live_client
    keys.append(KEY_SERVICE_LOCK)
    client.delete(KEY_SERVICE_LOCK)

    service = _service(client)
    assert service._acquire_service_lock() is True

    service._release_service_lock()

    assert not client.exists(KEY_SERVICE_LOCK)


def test_service_refresh_does_not_extend_another_processs_lock(live_client):
    """``_refresh_service_lock`` re-armed the TTL on whatever key was there.

    A service that lost its lock kept the NEW owner's lock alive from the
    outside — so the key stopped reflecting the live owner's liveness,
    which is the one thing a TTL on a singleton lock is for.
    """
    from attune.memory.cross_session.models import KEY_SERVICE_LOCK

    client, keys = live_client
    keys.append(KEY_SERVICE_LOCK)
    client.delete(KEY_SERVICE_LOCK)

    other_pid = os.getpid() + 1
    client.set(KEY_SERVICE_LOCK, other_pid, ex=5)

    _service(client)._refresh_service_lock()

    assert client.ttl(KEY_SERVICE_LOCK) <= 5, "a non-owner refreshed the live owner's lock TTL"


def test_service_refresh_still_extends_its_own_lock(live_client):
    from attune.memory.cross_session.models import (
        KEY_SERVICE_HEARTBEAT,
        KEY_SERVICE_LOCK,
        SERVICE_LOCK_TTL_SECONDS,
    )

    client, keys = live_client
    keys.extend([KEY_SERVICE_LOCK, KEY_SERVICE_HEARTBEAT])
    client.delete(KEY_SERVICE_LOCK)

    service = _service(client)
    assert service._acquire_service_lock() is True
    client.expire(KEY_SERVICE_LOCK, 5)

    service._refresh_service_lock()

    assert client.ttl(KEY_SERVICE_LOCK) > 5
    assert client.ttl(KEY_SERVICE_LOCK) <= SERVICE_LOCK_TTL_SECONDS
