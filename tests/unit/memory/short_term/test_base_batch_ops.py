"""Tests for BaseOperations._mget /._delete_many (single-round-trip batch ops).

These primitives replaced the N+1 per-key loops in sessions, facade,
conflicts, patterns, and working (2026-08-08 post-release self-review).
Covers mock mode, the no-client fallback, and the real-client path via
a stub Redis client.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from attune.memory.short_term.base import BaseOperations


class StubClient:
    """Minimal Redis client recording mget/delete calls."""

    def __init__(self, store: dict[str, str]):
        self.store = store
        self.mget_calls: list[list[str]] = []
        self.delete_calls: list[tuple[str, ...]] = []

    def mget(self, keys: list[str]) -> list[str | None]:
        self.mget_calls.append(list(keys))
        return [self.store.get(k) for k in keys]

    def delete(self, *keys: str) -> int:
        self.delete_calls.append(keys)
        return sum(1 for k in keys if self.store.pop(k, None) is not None)


class TestMget:
    def test_empty_keys_short_circuits(self):
        base = BaseOperations(use_mock=True)
        assert base._mget([]) == []

    def test_mock_mode_returns_aligned_values(self):
        base = BaseOperations(use_mock=True)
        base._set("a", "1")
        base._set("c", "3")
        assert base._mget(["a", "b", "c"]) == ["1", None, "3"]

    def test_real_client_single_round_trip(self):
        base = BaseOperations(use_mock=True)
        base.use_mock = False
        client = StubClient({"a": "1", "c": "3"})
        base._client = client
        assert base._mget(["a", "b", "c"]) == ["1", None, "3"]
        assert client.mget_calls == [["a", "b", "c"]]

    def test_no_client_degrades_to_none_values(self):
        base = BaseOperations(use_mock=True)
        base.use_mock = False
        base._client = None
        assert base._mget(["a", "b"]) == [None, None]


class TestDeleteMany:
    def test_empty_keys_short_circuits(self):
        base = BaseOperations(use_mock=True)
        assert base._delete_many([]) == 0

    def test_mock_mode_counts_deletions(self):
        base = BaseOperations(use_mock=True)
        base._set("a", "1")
        base._set("b", "2")
        assert base._delete_many(["a", "b", "missing"]) == 2
        assert base._get("a") is None

    def test_real_client_variadic_single_call(self):
        base = BaseOperations(use_mock=True)
        base.use_mock = False
        client = StubClient({"a": "1", "b": "2"})
        base._client = client
        assert base._delete_many(["a", "b", "missing"]) == 2
        assert client.delete_calls == [("a", "b", "missing")]
