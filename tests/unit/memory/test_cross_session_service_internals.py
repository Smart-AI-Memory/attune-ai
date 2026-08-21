"""Targeted tests for BackgroundService internals (cross_session/service).

Supplements tests/unit/memory/test_cross_session_service.py, covering the
lock-refresh, service-loop, stale-cleanup, and status-with-coordinator
branches it leaves uncovered (78% -> 100%). Uses a fake memory/client
and a controllable stop-event so the threaded loop runs deterministically
without a real Redis or a real thread.
"""

import pytest

import attune.memory.cross_session.service as svc
from attune.memory.cross_session.models import (
    KEY_SERVICE_HEARTBEAT,
    KEY_SERVICE_LOCK,
)
from attune.memory.cross_session.service import BackgroundService


class _FakeClient:
    def __init__(self):
        self.calls: list = []

    def expire(self, key, ttl):
        self.calls.append(("expire", key, ttl))

    def delete(self, key):
        self.calls.append(("delete", key))

    def set(self, key, value, **kwargs):
        # nx/ex ride along on the acquisition — library-review H2 removed
        # the follow-up EXPIRE, so this fake must accept them.
        self.calls.append(("set", key, kwargs))
        return True

    def eval(self, script, numkeys, *args):
        # Owner-checked release/refresh are ONE server-side script — a bare
        # EXPIRE or DELETE would re-arm or remove a lock this process may no
        # longer hold (library-review H6).
        self.calls.append(("eval", args[0], args[1:]))
        return 1


class _FakeMemory:
    def __init__(self, client, use_mock=False):
        self.use_mock = use_mock
        self._client = client


class _FakeSession:
    def to_dict(self):
        return {"id": "sess-1"}


class _FakeCoordinator:
    def __init__(self, sessions=None, agent_id="svc-1"):
        self.agent_id = agent_id
        self._sessions = sessions if sessions is not None else []
        self.closed = False

    def get_active_sessions(self):
        return self._sessions

    def close(self):
        self.closed = True


class _FakeEvent:
    """Stop-event whose wait() yields a preset sequence then True."""

    def __init__(self, returns):
        self._returns = list(returns)

    def wait(self, timeout):
        return self._returns.pop(0) if self._returns else True

    def set(self):
        pass

    def clear(self):
        pass


def _service(client="default"):
    if client == "default":
        client = _FakeClient()
    return BackgroundService(_FakeMemory(client))


# ===========================================================================
# __init__
# ===========================================================================


def test_init_rejects_mock_memory():
    with pytest.raises(ValueError, match="requires Redis"):
        BackgroundService(_FakeMemory(_FakeClient(), use_mock=True))


# ===========================================================================
# lock helpers
# ===========================================================================


def test_acquire_lock_without_client_returns_false():
    s = _service(client=None)
    assert s._acquire_service_lock() is False


def test_refresh_lock_extends_ttl_and_writes_heartbeat():
    client = _FakeClient()
    s = BackgroundService(_FakeMemory(client))
    s._refresh_service_lock()
    names = [c[0] for c in client.calls]
    assert "eval" in names and "set" in names
    # The TTL is re-armed only if this process still owns the key, inside
    # one script — a bare EXPIRE keeps ANOTHER service's lock alive.
    assert "expire" not in names
    assert any(c[0] == "eval" and c[1] == KEY_SERVICE_LOCK for c in client.calls)
    assert any(c[0] == "set" and c[1] == KEY_SERVICE_HEARTBEAT for c in client.calls)


def test_refresh_lock_without_client_is_noop():
    s = _service(client=None)
    s._refresh_service_lock()  # no exception


# ===========================================================================
# cleanup
# ===========================================================================


def test_cleanup_without_coordinator_noops():
    s = _service()
    s._cleanup_stale_sessions()  # _coordinator is None -> returns


def test_cleanup_with_coordinator_queries_sessions():
    s = _service()
    coord = _FakeCoordinator(sessions=[_FakeSession(), _FakeSession()])
    s._coordinator = coord
    s._cleanup_stale_sessions()  # exercises the active-sessions path


# ===========================================================================
# get_status
# ===========================================================================


def test_status_with_coordinator_lists_sessions():
    s = _service()
    s._coordinator = _FakeCoordinator(sessions=[_FakeSession()], agent_id="svc-9")
    status = s.get_status()
    assert status["agent_id"] == "svc-9"
    assert status["active_sessions"] == 1
    assert status["sessions"] == [{"id": "sess-1"}]


# ===========================================================================
# _service_loop
# ===========================================================================


def test_service_loop_runs_one_iteration_with_cleanup(monkeypatch):
    s = _service()
    s._stop_event = _FakeEvent([False])  # one iteration, then stop

    # Advance time so the cleanup interval (60s) elapses.
    ticks = iter([0.0, 1000.0, 1000.0, 1000.0, 1000.0])
    monkeypatch.setattr(svc.time, "time", lambda: next(ticks))

    refreshed = []
    cleaned = []
    monkeypatch.setattr(s, "_refresh_service_lock", lambda: refreshed.append(True))
    monkeypatch.setattr(s, "_cleanup_stale_sessions", lambda: cleaned.append(True))

    s._service_loop()
    assert refreshed == [True]
    assert cleaned == [True]  # interval elapsed -> cleanup fired


def test_service_loop_logs_exception_and_continues(monkeypatch):
    s = _service()
    s._stop_event = _FakeEvent([False])

    def boom():
        raise RuntimeError("redis blip")

    monkeypatch.setattr(s, "_refresh_service_lock", boom)
    # Should not raise — the loop swallows and logs.
    s._service_loop()
