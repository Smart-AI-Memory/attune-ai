"""Behavioral tests for Pagination (SCAN-based pagination).

Drives Pagination against fake base-operations in both mock-storage and
real-Redis-client modes, covering paging math, expiry filtering, the
client-None short-circuit, and cursor/has_more semantics for both
list_staged_patterns_paginated and scan_keys.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json

from attune.memory.short_term.pagination import Pagination
from attune.memory.types import AccessTier, AgentCredentials, StagedPattern

CREDS = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
STAGED = Pagination.PREFIX_STAGED


def _staged_json(pattern_id: str = "p1") -> str:
    sp = StagedPattern(
        pattern_id=pattern_id,
        agent_id="a1",
        pattern_type="algo",
        name="n",
        description="d",
    )
    return json.dumps(sp.to_dict())


class _Metrics:
    def __init__(self):
        self.ops: list[tuple[str, float]] = []

    def record_operation(self, name: str, latency_ms: float) -> None:
        self.ops.append((name, latency_ms))


class _MockBase:
    """Base in mock-storage mode: _mock_storage maps key -> (raw, expires)."""

    use_mock = True

    def __init__(self, mock_storage: dict):
        self._mock_storage = mock_storage
        self._metrics = _Metrics()


class _FakeClient:
    def __init__(self, scan_result: tuple, values: dict | None = None):
        self._scan_result = scan_result
        self._values = values or {}

    def scan(self, cursor: int, match: str, count: int):
        return self._scan_result

    def get(self, key):
        return self._values.get(key)


class _RealBase:
    """Base in real-client mode."""

    use_mock = False

    def __init__(self, client):
        self._client = client
        self._metrics = _Metrics()


class TestListPaginatedMockMode:
    def test_first_page_reports_has_more(self):
        storage = {
            f"{STAGED}1": (_staged_json("1"), None),
            f"{STAGED}2": (_staged_json("2"), None),
            f"{STAGED}3": (_staged_json("3"), None),
            "other:key": ("ignored", None),
        }
        base = _MockBase(storage)
        result = Pagination(base).list_staged_patterns_paginated(CREDS, cursor="0", count=2)

        assert len(result.items) == 2
        assert result.cursor == "2"
        assert result.has_more is True
        assert result.total_scanned == 2
        # Latency metric recorded.
        assert base._metrics.ops[0][0] == "list_paginated"

    def test_last_page_resets_cursor(self):
        storage = {f"{STAGED}{i}": (_staged_json(str(i)), None) for i in range(3)}
        base = _MockBase(storage)
        result = Pagination(base).list_staged_patterns_paginated(CREDS, cursor="2", count=2)

        assert len(result.items) == 1
        assert result.cursor == "0"
        assert result.has_more is False

    def test_expired_entries_are_filtered(self):
        storage = {
            f"{STAGED}1": (_staged_json("1"), None),
            f"{STAGED}2": (_staged_json("2"), 1.0),  # expires far in the past
        }
        base = _MockBase(storage)
        result = Pagination(base).list_staged_patterns_paginated(CREDS, cursor="0", count=10)

        # Both keys scanned, but the expired one is dropped from items.
        assert result.total_scanned == 2
        assert len(result.items) == 1
        assert result.items[0].pattern_id == "1"


class TestListPaginatedRealClient:
    def test_client_none_returns_empty(self):
        result = Pagination(_RealBase(client=None)).list_staged_patterns_paginated(CREDS)

        assert result.items == []
        assert result.cursor == "0"
        assert result.has_more is False

    def test_scan_parses_values_and_skips_missing(self):
        client = _FakeClient(
            scan_result=(5, [f"{STAGED}1", f"{STAGED}2"]),
            values={f"{STAGED}1": _staged_json("1")},  # key 2 missing -> skipped
        )
        result = Pagination(_RealBase(client)).list_staged_patterns_paginated(CREDS, cursor="0")

        assert len(result.items) == 1
        assert result.items[0].pattern_id == "1"
        assert result.cursor == "5"
        assert result.has_more is True
        assert result.total_scanned == 2

    def test_zero_cursor_means_no_more(self):
        client = _FakeClient(
            scan_result=(0, [f"{STAGED}1"]),
            values={f"{STAGED}1": _staged_json("1")},
        )
        result = Pagination(_RealBase(client)).list_staged_patterns_paginated(CREDS)

        assert result.has_more is False
        assert result.cursor == "0"


class TestScanKeys:
    def test_mock_mode_paginates_matching_keys(self):
        storage = {
            "empathy:session:a": ("v", None),
            "empathy:session:b": ("v", None),
            "empathy:other:c": ("v", None),
        }
        base = _MockBase(storage)
        result = Pagination(base).scan_keys("empathy:session:*", cursor="0", count=1)

        assert result.items == ["empathy:session:a"]
        assert result.cursor == "1"
        assert result.has_more is True

    def test_mock_mode_last_page_resets_cursor(self):
        storage = {"empathy:session:a": ("v", None)}
        base = _MockBase(storage)
        result = Pagination(base).scan_keys("empathy:session:*", cursor="0", count=10)

        assert result.items == ["empathy:session:a"]
        assert result.cursor == "0"
        assert result.has_more is False

    def test_real_client_none_returns_empty(self):
        result = Pagination(_RealBase(client=None)).scan_keys("empathy:*")

        assert result.items == []
        assert result.has_more is False

    def test_real_client_returns_stringified_keys(self):
        client = _FakeClient(scan_result=(3, ["k1", "k2"]))
        result = Pagination(_RealBase(client)).scan_keys("empathy:*", cursor="0")

        assert result.items == ["k1", "k2"]
        assert result.cursor == "3"
        assert result.has_more is True
