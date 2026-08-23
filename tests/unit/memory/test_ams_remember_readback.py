"""``AMSMemoryBackend.remember`` returns True only after a readback.

Round table ``q-post-redis-repair-broken-features-001`` (2026-08-23): AMS
acknowledges ``POST /v1/long-term-memory/`` with 200 BEFORE the Redis
write — 2,437 acks and zero persisted records while its Redis auth was
dead. The HTTP ack is therefore never the receipt; ``remember`` must read
the id back. Same fixture strategy as ``test_ams_forget.py``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from agent_memory_client.exceptions import MemoryNotFoundError

import attune_redis.memory as ams
from attune_redis.memory import AMSMemoryBackend


@pytest.fixture
def backend(monkeypatch):
    be = object.__new__(AMSMemoryBackend)
    be._client = MagicMock()
    be._namespace = "itest-ns"
    be._session_id = "sess"
    be._user_id = None
    monkeypatch.setattr(ams, "_run_sync", _drive)
    monkeypatch.setattr(ams.time, "sleep", lambda s: None)
    return be


def _drive(coro):
    """Run a coroutine (the readback is wrapped in asyncio.wait_for); pass
    plain values through as the identity runner used elsewhere does."""
    import asyncio

    if asyncio.iscoroutine(coro):
        return asyncio.run(coro)
    return coro


def test_remember_true_only_after_readback(backend):
    backend._client.get_long_term_memory = AsyncMock(return_value={"id": "m1"})
    assert backend.remember("finding", memory_id="m1") is True
    backend._client.get_long_term_memory.assert_called_with("m1")


def test_acked_but_unreadable_write_returns_false(backend, caplog):
    """The exact 2026-08-23 failure: create acks, readback never succeeds."""
    backend._client.get_long_term_memory.side_effect = MemoryNotFoundError("404")
    assert backend.remember("finding", memory_id="m1") is False
    assert backend._client.create_long_term_memory.called
    assert backend._client.get_long_term_memory.call_count == ams._READBACK_ATTEMPTS
    assert "remember_unconfirmed" in caplog.text


def test_readback_tolerates_index_lag(backend):
    """A miss followed by a hit within the retry budget still confirms."""
    backend._client.get_long_term_memory = AsyncMock(
        side_effect=[MemoryNotFoundError("404"), {"id": "m1"}]
    )
    assert backend.remember("finding", memory_id="m1") is True
    assert backend._client.get_long_term_memory.call_count == 2


def test_create_failure_short_circuits_without_readback(backend):
    backend._client.create_long_term_memory.side_effect = RuntimeError("boom")
    assert backend.remember("finding", memory_id="m1") is False
    backend._client.get_long_term_memory.assert_not_called()


def test_unexpected_readback_error_degrades_to_false(backend):
    """An error outside the transport set must not escape remember()."""
    backend._client.get_long_term_memory.side_effect = RuntimeError("loop closed")
    assert backend.remember("finding", memory_id="m1") is False


def test_readback_attempt_is_time_bounded(backend, monkeypatch):
    """A hung AMS cannot hold the Stop hook: each attempt times out fast."""
    import asyncio

    async def _hang(_id):
        await asyncio.sleep(60)

    monkeypatch.setattr(ams, "_READBACK_TIMEOUT_S", 0.05)
    backend._client.get_long_term_memory = _hang
    assert backend.remember("finding", memory_id="m1") is False
