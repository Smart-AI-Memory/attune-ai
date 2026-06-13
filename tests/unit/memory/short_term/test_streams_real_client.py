"""Real-Redis-path tests for StreamManager.

The existing `tests/unit/memory/test_short_term_streams.py` exercises the
in-memory MOCK path (`use_mock=True`). This complementary suite covers the
REAL Redis branches — the `_client is None` guards, the `xadd`/`xrange`/
`xread` calls, the result-conversion comprehensions, and the
`str(entry_id) if entry_id else None` ternary in `append()` — by injecting
a `MagicMock` Redis client (`use_mock=False`). No live Redis is required.

These are the branches behind the module's 67.2% coverage gap; pinning the
exact client-call arguments and both ternary arms also kills the relevant
operator/return mutations.

Coverage (with the existing mock suite): `streams.py` 67.2% -> 100%.

Mutation status (mutmut 2.4.4, both suites as runner): ``57 mutants ->
43 killed, 14 survived``. All 14 survivors are documented equivalents:
the unused module ``logger``; the `PermissionError`/metric-label strings
(substring ``match=`` can't kill ``XX``-wrapped text); the mock-path
entry-id timestamp formatting and the latency-arithmetic on both paths
(timing-dependent values, not behaviorally asserted); and the mock trim
``>`` boundary (slicing a max_len-length list to ``[-max_len:]`` is a
no-op, so ``>`` vs ``>=`` is unobservable). Killable kill-rate 43/43 = 100%.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from attune.memory.short_term import AccessTier, AgentCredentials
from attune.memory.short_term.streams import StreamManager

pytestmark = pytest.mark.unit


@pytest.fixture
def creds() -> AgentCredentials:
    """Contributor credentials (can write to streams)."""
    return AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)


def make_base(client):
    """Fake BaseOperations in real (non-mock) mode with an injected client."""
    return SimpleNamespace(use_mock=False, _client=client, _metrics=MagicMock())


@pytest.fixture
def client() -> MagicMock:
    return MagicMock()


@pytest.fixture
def manager(client) -> StreamManager:
    return StreamManager(make_base(client))


class TestAppendRealClient:
    def test_returns_none_when_client_is_none(self, creds):
        mgr = StreamManager(make_base(None))
        assert mgr.append("audit", {"action": "x"}, creds) is None

    def test_calls_xadd_with_prefixed_stream_and_maxlen(self, manager, client, creds):
        client.xadd.return_value = "1700000000000-0"
        result = manager.append("audit", {"action": "promote"}, creds, max_len=500)
        assert result == "1700000000000-0"
        client.xadd.assert_called_once()
        args, kwargs = client.xadd.call_args
        assert args[0] == "stream:audit"
        assert kwargs["maxlen"] == 500
        # entry carries agent_id + timestamp + serialized payload
        entry = args[1]
        assert entry["agent_id"] == "agent_1"
        assert "timestamp" in entry
        assert entry["action"] == "promote"

    def test_returns_str_of_non_string_entry_id(self, manager, client, creds):
        client.xadd.return_value = 12345  # redis may hand back bytes/int-ish
        assert manager.append("audit", {"a": "b"}, creds) == "12345"

    def test_returns_none_when_xadd_returns_falsy(self, manager, client, creds):
        client.xadd.return_value = None
        assert manager.append("audit", {"a": "b"}, creds) is None

    def test_records_metric_on_real_append(self, manager, client, creds):
        client.xadd.return_value = "1-0"
        base = manager._base
        manager.append("audit", {"a": "b"}, creds)
        base._metrics.record_operation.assert_called_once()
        assert base._metrics.record_operation.call_args[0][0] == "stream_append"

    def test_permission_denied_before_touching_client(self, client):
        observer = AgentCredentials("obs", AccessTier.OBSERVER)
        mgr = StreamManager(make_base(client))
        with pytest.raises(PermissionError, match="CONTRIBUTOR"):
            mgr.append("audit", {"a": "b"}, observer)
        client.xadd.assert_not_called()

    def test_default_max_len_reaches_client(self, manager, client, creds):
        """The default max_len (10000) must be passed through to xadd."""
        client.xadd.return_value = "1-0"
        manager.append("audit", {"a": "b"}, creds)
        assert client.xadd.call_args.kwargs["maxlen"] == 10000

    def test_metric_records_numeric_latency(self, manager, client, creds):
        """record_operation's 2nd arg is a real latency, not None."""
        client.xadd.return_value = "1-0"
        manager.append("audit", {"a": "b"}, creds)
        latency = manager._base._metrics.record_operation.call_args[0][1]
        assert isinstance(latency, float)
        assert latency >= 0


class TestReadRealClient:
    def test_returns_empty_when_client_is_none(self, creds):
        mgr = StreamManager(make_base(None))
        assert mgr.read("audit", creds) == []

    def test_calls_xrange_and_converts_result(self, manager, client, creds):
        client.xrange.return_value = [
            ("1-0", {"agent_id": "a", "action": "x"}),
            ("2-0", {"agent_id": "b", "action": "y"}),
        ]
        out = manager.read("audit", creds, start_id="0", count=50)
        client.xrange.assert_called_once_with("stream:audit", min="0", count=50)
        # entry ids stringified; data preserved
        assert out == [
            ("1-0", {"agent_id": "a", "action": "x"}),
            ("2-0", {"agent_id": "b", "action": "y"}),
        ]

    def test_empty_xrange_yields_empty_list(self, manager, client, creds):
        client.xrange.return_value = []
        assert manager.read("audit", creds) == []

    def test_defaults_reach_client(self, manager, client, creds):
        """Default start_id ('0') and count (100) must reach xrange."""
        client.xrange.return_value = []
        manager.read("audit", creds)
        client.xrange.assert_called_once_with("stream:audit", min="0", count=100)


class TestReadNewRealClient:
    def test_returns_empty_when_client_is_none(self, creds):
        mgr = StreamManager(make_base(None))
        assert mgr.read_new("audit", creds) == []

    def test_calls_xread_with_block_and_count(self, manager, client, creds):
        client.xread.return_value = [
            ("stream:audit", [("1-0", {"action": "x"})]),
        ]
        out = manager.read_new("audit", creds, block_ms=5000, count=10)
        client.xread.assert_called_once_with({"stream:audit": "$"}, block=5000, count=10)
        assert out == [("1-0", {"action": "x"})]

    def test_falsy_xread_result_yields_empty(self, manager, client, creds):
        client.xread.return_value = None
        assert manager.read_new("audit", creds) == []

    def test_flattens_multiple_streams_and_entries(self, manager, client, creds):
        client.xread.return_value = [
            ("stream:audit", [("1-0", {"k": "1"}), ("2-0", {"k": "2"})]),
        ]
        out = manager.read_new("audit", creds)
        assert out == [("1-0", {"k": "1"}), ("2-0", {"k": "2"})]

    def test_defaults_reach_client(self, manager, client, creds):
        """Default block_ms (0) and count (100) must reach xread."""
        client.xread.return_value = None
        manager.read_new("audit", creds)
        client.xread.assert_called_once_with({"stream:audit": "$"}, block=0, count=100)


class TestMockTrim:
    """Mock-mode max_len trimming keeps the *last* max_len entries."""

    def _mock_manager(self):
        base = SimpleNamespace(use_mock=True, _metrics=MagicMock())
        return StreamManager(base)

    def test_trim_keeps_last_max_len_entries(self, creds):
        mgr = self._mock_manager()
        for i in range(5):
            mgr.append("audit", {"n": str(i)}, creds, max_len=3)
        kept = [data["n"] for _eid, data in mgr.read("audit", creds)]
        # Slice direction matters: [-max_len:] keeps the LAST three (2,3,4),
        # whereas [max_len:] would drop the first three and keep too few.
        assert kept == ["2", "3", "4"]
