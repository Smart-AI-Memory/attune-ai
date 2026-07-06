"""Unit tests for ``AMSMemoryBackend.forget`` and the
``redis_memory_forget`` MCP tool (issue #1264).

``forget(ids)`` is the precise-removal counterpart to ``prune()`` —
deleting specific long-term records by the ``id`` values that
``search()``/``recent()`` return. Same test strategy as
``test_ams_prune.py``: fake client, ``_run_sync`` as identity
passthrough, no live AMS server required.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

import attune_redis.memory as ams
from attune_redis.mcp_tools import (
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    handle_redis_memory_forget,
)
from attune_redis.memory import AMSMemoryBackend


class _FakeAck:
    """AMS acks deletes with a status string, not a numeric field."""

    def __init__(self, status: str) -> None:
        self.status = status


@pytest.fixture
def backend(monkeypatch):
    """An ``AMSMemoryBackend`` with a fake client, bypassing the real
    ``__init__`` (which would construct a live HTTP client)."""
    be = object.__new__(AMSMemoryBackend)
    be._client = MagicMock()
    be._namespace = "itest-ns"
    monkeypatch.setattr(ams, "_run_sync", lambda coro: coro)
    return be


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------


def test_forget_parses_deleted_count_from_status(backend):
    backend._client.delete_long_term_memories.return_value = _FakeAck("ok, deleted 3 memories")
    assert backend.forget(["a", "b", "c"]) == 3
    backend._client.delete_long_term_memories.assert_called_once_with(["a", "b", "c"])


def test_forget_bare_ok_falls_back_to_len_ids(backend):
    backend._client.delete_long_term_memories.return_value = _FakeAck("ok")
    assert backend.forget(["a", "b"]) == 2


def test_forget_empty_ids_short_circuits(backend):
    assert backend.forget([]) == 0
    backend._client.delete_long_term_memories.assert_not_called()


def test_forget_non_ok_status_returns_zero(backend):
    backend._client.delete_long_term_memories.return_value = _FakeAck("error: nope")
    assert backend.forget(["a"]) == 0


def test_forget_swallows_client_error(backend):
    backend._client.delete_long_term_memories.side_effect = RuntimeError("AMS 503")
    assert backend.forget(["a"]) == 0


# ---------------------------------------------------------------------------
# MCP tool surface
# ---------------------------------------------------------------------------


def test_tool_registered_in_definitions_and_handlers():
    assert "redis_memory_forget" in TOOL_DEFINITIONS
    assert TOOL_DEFINITIONS["redis_memory_forget"]["input_schema"]["required"] == ["ids"]
    assert TOOL_HANDLERS["redis_memory_forget"] is handle_redis_memory_forget


def test_handler_deletes_by_ids(backend):
    server = MagicMock()
    server._redis_backend = backend
    backend._client.delete_long_term_memories.return_value = _FakeAck("ok, deleted 2 memories")

    result = asyncio.run(handle_redis_memory_forget(server, {"ids": ["x", "y"]}))

    assert result == {
        "success": True,
        "requested": 2,
        "deleted": 2,
        "source": "redis-ams",
    }


def test_handler_rejects_non_list_ids(backend):
    server = MagicMock()
    server._redis_backend = backend

    result = asyncio.run(handle_redis_memory_forget(server, {"ids": "not-a-list"}))

    assert result["success"] is False
    assert "list of record-ID strings" in result["error"]
    backend._client.delete_long_term_memories.assert_not_called()


def test_handler_reports_failure_when_nothing_deleted(backend):
    server = MagicMock()
    server._redis_backend = backend
    backend._client.delete_long_term_memories.side_effect = RuntimeError("AMS down")

    result = asyncio.run(handle_redis_memory_forget(server, {"ids": ["x"]}))

    assert result["success"] is False
    assert result["deleted"] == 0
