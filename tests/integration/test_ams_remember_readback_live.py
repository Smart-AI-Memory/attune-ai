"""Non-mocked boundary test: ``remember`` is a receipt, not an ack.

Runs only when a real Agent Memory Server answers ``/v1/health`` (skips in
CI). Positive: a write reads back and the record is visible by id over the
real transport. Negative: with the create call neutralised, the REAL readback
404s and ``remember`` must return False — the shape of the 2026-08-23 silent
stash loss, where AMS acked every create while persisting nothing.
"""

from __future__ import annotations

import os
import urllib.request
import uuid

import pytest

AMS_URL = os.environ.get("ATTUNE_AMS_URL", "http://localhost:8000")


def _ams_up() -> bool:
    try:
        with urllib.request.urlopen(f"{AMS_URL}/v1/health", timeout=2) as r:  # noqa: S310
            return r.status == 200
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _ams_up(), reason="no live AMS at ATTUNE_AMS_URL")


@pytest.fixture
def backend():
    from attune_redis.memory import AMSMemoryBackend

    be = AMSMemoryBackend()
    be._namespace = f"itest-readback-{uuid.uuid4().hex[:8]}"
    yield be
    be.close()


def test_live_write_reads_back(backend):
    from attune_redis.memory import _run_sync

    mid = f"itest-{uuid.uuid4().hex}"
    try:
        assert backend.remember("live readback receipt", memory_id=mid) is True
        rec = _run_sync(backend._client.get_long_term_memory(mid))
        assert rec.id == mid
    finally:
        backend.forget([mid])


def test_live_unpersisted_write_is_not_a_success(backend, monkeypatch):
    """Real transport, real 404: an acked-but-absent record returns False."""

    async def _ack_without_write(*args, **kwargs):
        return None

    monkeypatch.setattr(backend._client, "create_long_term_memory", _ack_without_write)
    assert backend.remember("never persisted", memory_id=f"itest-{uuid.uuid4().hex}") is False
