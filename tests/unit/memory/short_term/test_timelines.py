"""Behavioral tests for TimelineManager (sorted-set time windows).

Drives TimelineManager in both mock and real-client modes covering
add (access control, sorted insertion, real zadd), query (window filter,
offset/limit slice, real zrangebyscore), and count (window count, real
zcount), plus the client-None short-circuits.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from attune.memory.short_term.timelines import TimelineManager
from attune.memory.types import AccessTier, AgentCredentials, TimeWindowQuery

CONTRIB = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
OBSERVER = AgentCredentials("watcher", AccessTier.OBSERVER)


class _MockBase:
    use_mock = True
    _client = None


class _RealBase:
    use_mock = False

    def __init__(self, client):
        self._client = client


class _FakeClient:
    def __init__(self):
        self.zadds: list[tuple] = []
        self.zrange_result: list[str] = []
        self.zcount_result = 0

    def zadd(self, key, mapping):
        self.zadds.append((key, mapping))

    def zrangebyscore(self, key, min, max, start, num):  # noqa: A002
        return self.zrange_result

    def zcount(self, key, min, max):  # noqa: A002
        return self.zcount_result


def _at(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute)


class TestAdd:
    def test_observer_cannot_add(self):
        with pytest.raises(PermissionError, match="cannot write to timeline"):
            TimelineManager(_MockBase()).add("evts", "e1", {}, OBSERVER)

    def test_mock_inserts_sorted_by_score(self):
        tm = TimelineManager(_MockBase())
        assert tm.add("evts", "late", {"i": 1}, CONTRIB, timestamp=_at(12)) is True
        assert tm.add("evts", "early", {"i": 2}, CONTRIB, timestamp=_at(10)) is True

        sset = tm._mock_sorted_sets["timeline:evts"]
        assert len(sset) == 2
        # Ascending by score -> the 10:00 event sorts first.
        assert sset[0][0] < sset[1][0]
        assert json.loads(sset[0][1])["event_id"] == "early"

    def test_real_client_none_returns_false(self):
        assert TimelineManager(_RealBase(None)).add("e", "e1", {}, CONTRIB) is False

    def test_real_client_zadds(self):
        client = _FakeClient()
        ok = TimelineManager(_RealBase(client)).add("e", "e1", {"a": 1}, CONTRIB)

        assert ok is True
        assert client.zadds[0][0] == "timeline:e"


class TestQuery:
    def test_mock_absent_timeline_returns_empty(self):
        assert TimelineManager(_MockBase()).query("nope", CONTRIB) == []

    def test_mock_filters_window(self):
        tm = TimelineManager(_MockBase())
        for i, h in enumerate([9, 10, 11, 12]):
            tm.add("evts", f"e{i}", {}, CONTRIB, timestamp=_at(h))

        q = TimeWindowQuery(start_time=_at(10), end_time=_at(11), limit=10)
        res = tm.query("evts", CONTRIB, q)

        assert [r["event_id"] for r in res] == ["e1", "e2"]

    def test_mock_offset_and_limit_slice(self):
        tm = TimelineManager(_MockBase())
        for i in range(5):
            tm.add("evts", f"e{i}", {}, CONTRIB, timestamp=_at(8, i))

        q = TimeWindowQuery(limit=2, offset=1)
        res = tm.query("evts", CONTRIB, q)

        assert [r["event_id"] for r in res] == ["e1", "e2"]

    def test_real_client_none_returns_empty(self):
        assert TimelineManager(_RealBase(None)).query("e", CONTRIB) == []

    def test_real_client_parses_results(self):
        client = _FakeClient()
        client.zrange_result = [json.dumps({"event_id": "e1"})]

        res = TimelineManager(_RealBase(client)).query("e", CONTRIB)

        assert res == [{"event_id": "e1"}]


class TestCount:
    def test_mock_absent_timeline_returns_zero(self):
        assert TimelineManager(_MockBase()).count("nope", CONTRIB) == 0

    def test_mock_counts_window(self):
        tm = TimelineManager(_MockBase())
        for h in [9, 10, 11]:
            tm.add("evts", "e", {}, CONTRIB, timestamp=_at(h))

        q = TimeWindowQuery(start_time=_at(10), end_time=_at(12))
        assert tm.count("evts", CONTRIB, q) == 2

    def test_real_client_none_returns_zero(self):
        assert TimelineManager(_RealBase(None)).count("e", CONTRIB) == 0

    def test_real_client_zcount(self):
        client = _FakeClient()
        client.zcount_result = 7
        assert TimelineManager(_RealBase(client)).count("e", CONTRIB) == 7
