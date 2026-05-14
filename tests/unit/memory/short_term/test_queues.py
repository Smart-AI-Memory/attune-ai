"""Tests for `attune.memory.short_term.queues.QueueManager`.

Strategy: real `QueueManager` instance composed with a real
`BaseOperations` (in two modes — `use_mock=True` for the
in-memory list path and `use_mock=False` with a `MagicMock`
swapped onto `_base._client` for the real-Redis branches).
Round-trips real JSON payloads end-to-end; no mock of
`QueueManager` itself.

Covers:
- Mock-mode push/pop/length/peek (already exercised by other
  suites, locked down here for explicit guard against regression).
- Real-Redis path (`use_mock=False` + `_client=MagicMock()`):
  push priority vs normal (lpush vs rpush), pop blocking
  (blpop) and non-blocking (lpop), each with result + no-result
  branches, length, peek.
- Defensive `client is None` returns: push → 0, pop → None,
  length → 0, peek → [].
- Permission gating: CONTRIBUTOR+ required for push;
  pop/length/peek don't gate (matches public contract).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from attune.memory.short_term.base import BaseOperations
from attune.memory.short_term.queues import QueueManager
from attune.memory.types import AccessTier, AgentCredentials

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_base() -> BaseOperations:
    """Real BaseOperations in mock mode (in-memory)."""
    return BaseOperations(use_mock=True)


@pytest.fixture
def mock_queue(mock_base: BaseOperations) -> QueueManager:
    return QueueManager(mock_base)


@pytest.fixture
def real_base_with_client() -> tuple[BaseOperations, MagicMock]:
    """BaseOperations in `use_mock=False` mode with a fake client.

    We don't actually connect to Redis — we drop a `MagicMock` onto
    `_base._client` so the real-Redis branches in QueueManager fire
    and we can assert on call args.

    Constructing BaseOperations(use_mock=False) on a host without
    Redis can trigger an internal `_create_client_with_retry` that
    blocks for ~17s (per CLAUDE.md "xdist worker crashes on Windows
    can come from repeated socket probes"). Patch the retry to skip.
    """
    from unittest.mock import patch as _patch

    with _patch(
        "attune.memory.short_term.base.BaseOperations._create_client_with_retry",
        return_value=None,
    ):
        base = BaseOperations(use_mock=False)
    # BaseOperations auto-flips use_mock to True when Redis auto-detect
    # finds the server unreachable. Force it back to False so the
    # real-Redis branches in QueueManager fire against our MagicMock
    # client. See CLAUDE.md "xdist worker crashes on Windows can come
    # from repeated socket probes" for the underlying constraint.
    base.use_mock = False
    client = MagicMock()
    base._client = client
    return base, client


@pytest.fixture
def real_queue_with_client(
    real_base_with_client: tuple[BaseOperations, MagicMock],
) -> tuple[QueueManager, MagicMock]:
    base, client = real_base_with_client
    return QueueManager(base), client


@pytest.fixture
def real_base_no_client() -> BaseOperations:
    """BaseOperations(use_mock=False) with _client=None (Redis down)."""
    from unittest.mock import patch as _patch

    with _patch(
        "attune.memory.short_term.base.BaseOperations._create_client_with_retry",
        return_value=None,
    ):
        base = BaseOperations(use_mock=False)
    # Force-disable auto-flip (see real_base_with_client docstring for why).
    base.use_mock = False
    base._client = None
    return base


@pytest.fixture
def contributor_creds() -> AgentCredentials:
    return AgentCredentials("contributor", AccessTier.CONTRIBUTOR)


@pytest.fixture
def observer_creds() -> AgentCredentials:
    return AgentCredentials("observer", AccessTier.OBSERVER)


# ---------------------------------------------------------------------------
# Permission gating
# ---------------------------------------------------------------------------


class TestPushPermissions:
    def test_observer_cannot_push(
        self,
        mock_queue: QueueManager,
        observer_creds: AgentCredentials,
    ) -> None:
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            mock_queue.push("any-queue", {"task": "x"}, observer_creds)

    def test_contributor_can_push(
        self,
        mock_queue: QueueManager,
        contributor_creds: AgentCredentials,
    ) -> None:
        new_len = mock_queue.push("q", {"task": "x"}, contributor_creds)
        assert new_len == 1


# ---------------------------------------------------------------------------
# Mock mode (in-memory) — round-trip behavior
# ---------------------------------------------------------------------------


class TestMockMode:
    def test_push_pop_fifo(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        mock_queue.push("q", {"n": 1}, contributor_creds)
        mock_queue.push("q", {"n": 2}, contributor_creds)
        first = mock_queue.pop("q", contributor_creds)
        second = mock_queue.pop("q", contributor_creds)
        assert first is not None and second is not None
        assert first["task"] == {"n": 1}
        assert second["task"] == {"n": 2}
        assert first["queued_by"] == "contributor"

    def test_push_priority_jumps_to_front(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        mock_queue.push("q", {"n": 1}, contributor_creds)
        mock_queue.push("q", {"n": 2}, contributor_creds, priority=True)
        # priority=True inserts at index 0
        first = mock_queue.pop("q", contributor_creds)
        assert first is not None and first["task"] == {"n": 2}

    def test_pop_empty_queue_returns_none(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        assert mock_queue.pop("never-pushed", contributor_creds) is None

    def test_pop_after_drain_returns_none(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        mock_queue.push("q", {"n": 1}, contributor_creds)
        mock_queue.pop("q", contributor_creds)
        assert mock_queue.pop("q", contributor_creds) is None

    def test_length_empty(self, mock_queue: QueueManager) -> None:
        assert mock_queue.length("nonexistent") == 0

    def test_length_after_pushes(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        mock_queue.push("q", {"n": 1}, contributor_creds)
        mock_queue.push("q", {"n": 2}, contributor_creds)
        assert mock_queue.length("q") == 2

    def test_peek_returns_first_n_without_consuming(
        self,
        mock_queue: QueueManager,
        contributor_creds: AgentCredentials,
    ) -> None:
        for i in range(5):
            mock_queue.push("q", {"n": i}, contributor_creds)
        peeked = mock_queue.peek("q", contributor_creds, count=3)
        assert len(peeked) == 3
        assert [p["task"]["n"] for p in peeked] == [0, 1, 2]
        # Peek must not consume — length still 5.
        assert mock_queue.length("q") == 5

    def test_peek_empty(
        self, mock_queue: QueueManager, contributor_creds: AgentCredentials
    ) -> None:
        assert mock_queue.peek("nonexistent", contributor_creds) == []


# ---------------------------------------------------------------------------
# Real-Redis path — push
# ---------------------------------------------------------------------------


class TestRealRedisPush:
    def test_push_normal_uses_rpush(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        client.rpush.return_value = 5
        result = q.push("tasks", {"a": 1}, contributor_creds)
        assert result == 5
        client.rpush.assert_called_once()
        client.lpush.assert_not_called()
        # Payload is a JSON-serialized envelope, key uses PREFIX_QUEUE.
        args, _ = client.rpush.call_args
        assert args[0] == f"{QueueManager.PREFIX_QUEUE}tasks"
        envelope = json.loads(args[1])
        assert envelope["task"] == {"a": 1}
        assert envelope["queued_by"] == "contributor"
        assert "queued_at" in envelope

    def test_push_priority_uses_lpush(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        client.lpush.return_value = 1
        result = q.push("tasks", {"a": 1}, contributor_creds, priority=True)
        assert result == 1
        client.lpush.assert_called_once()
        client.rpush.assert_not_called()

    def test_push_client_none_returns_zero(
        self,
        real_base_no_client: BaseOperations,
        contributor_creds: AgentCredentials,
    ) -> None:
        q = QueueManager(real_base_no_client)
        assert q.push("tasks", {"a": 1}, contributor_creds) == 0


# ---------------------------------------------------------------------------
# Real-Redis path — pop
# ---------------------------------------------------------------------------


class TestRealRedisPop:
    def test_pop_non_blocking_with_result(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        envelope = json.dumps({"task": {"a": 1}, "queued_by": "x", "queued_at": "now"})
        client.lpop.return_value = envelope

        result = q.pop("tasks", contributor_creds)
        assert result is not None
        assert result["task"] == {"a": 1}
        client.lpop.assert_called_once_with(f"{QueueManager.PREFIX_QUEUE}tasks")
        client.blpop.assert_not_called()

    def test_pop_non_blocking_empty(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        client.lpop.return_value = None
        assert q.pop("tasks", contributor_creds) is None

    def test_pop_blocking_with_result(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        envelope = json.dumps({"task": {"a": 1}, "queued_by": "x", "queued_at": "now"})
        # blpop returns (key, payload) tuple
        client.blpop.return_value = (b"queue:tasks", envelope)

        result = q.pop("tasks", contributor_creds, timeout=5)
        assert result is not None
        assert result["task"] == {"a": 1}
        client.blpop.assert_called_once_with(f"{QueueManager.PREFIX_QUEUE}tasks", timeout=5)
        client.lpop.assert_not_called()

    def test_pop_blocking_empty_returns_none(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        client.blpop.return_value = None
        assert q.pop("tasks", contributor_creds, timeout=5) is None

    def test_pop_client_none_returns_none(
        self,
        real_base_no_client: BaseOperations,
        contributor_creds: AgentCredentials,
    ) -> None:
        q = QueueManager(real_base_no_client)
        assert q.pop("tasks", contributor_creds) is None


# ---------------------------------------------------------------------------
# Real-Redis path — length + peek
# ---------------------------------------------------------------------------


class TestRealRedisLength:
    def test_length_uses_llen(self, real_queue_with_client: tuple[QueueManager, MagicMock]) -> None:
        q, client = real_queue_with_client
        client.llen.return_value = 42
        assert q.length("tasks") == 42
        client.llen.assert_called_once_with(f"{QueueManager.PREFIX_QUEUE}tasks")

    def test_length_client_none_returns_zero(self, real_base_no_client: BaseOperations) -> None:
        q = QueueManager(real_base_no_client)
        assert q.length("tasks") == 0


class TestRealRedisPeek:
    def test_peek_uses_lrange(
        self,
        real_queue_with_client: tuple[QueueManager, MagicMock],
        contributor_creds: AgentCredentials,
    ) -> None:
        q, client = real_queue_with_client
        envelopes = [
            json.dumps({"task": {"n": 0}, "queued_by": "x", "queued_at": "t"}),
            json.dumps({"task": {"n": 1}, "queued_by": "x", "queued_at": "t"}),
            json.dumps({"task": {"n": 2}, "queued_by": "x", "queued_at": "t"}),
        ]
        client.lrange.return_value = envelopes

        result = q.peek("tasks", contributor_creds, count=3)
        assert len(result) == 3
        assert [r["task"]["n"] for r in result] == [0, 1, 2]
        # lrange uses inclusive end index → count - 1
        client.lrange.assert_called_once_with(f"{QueueManager.PREFIX_QUEUE}tasks", 0, 2)

    def test_peek_client_none_returns_empty(
        self,
        real_base_no_client: BaseOperations,
        contributor_creds: AgentCredentials,
    ) -> None:
        q = QueueManager(real_base_no_client)
        assert q.peek("tasks", contributor_creds) == []


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_prefix_constant(self) -> None:
        # Changing this orphans every existing Redis key — lock it.
        assert QueueManager.PREFIX_QUEUE == "queue:"

    def test_init_stores_base_and_inits_mock_lists(self, mock_base: BaseOperations) -> None:
        q = QueueManager(mock_base)
        assert q._base is mock_base
        assert q._mock_lists == {}
