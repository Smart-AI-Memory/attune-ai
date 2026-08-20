"""Tests for ConversationSummaryIndex corrupt-store tolerance.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from types import SimpleNamespace

from attune.memory.summary_index import ConversationSummaryIndex, _loads_list


class _StubClient:
    """Redis stand-in serving one corrupt summary hash."""

    def __init__(self, summary: dict[str, str]) -> None:
        self._summary = summary

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._summary)

    def smembers(self, key: str) -> set[str]:
        return {"sess-1"}


class TestLoadsList:
    def test_valid_list_round_trips(self) -> None:
        assert _loads_list('["a", "b"]') == ["a", "b"]

    def test_corrupt_json_degrades_to_empty(self) -> None:
        assert _loads_list("{corrupt json") == []

    def test_non_list_json_degrades_to_empty(self) -> None:
        assert _loads_list('{"not": "a list"}') == []

    def test_none_degrades_to_empty(self) -> None:
        assert _loads_list(None) == []  # type: ignore[arg-type]


class TestCorruptStoreDegrades:
    def test_recall_decisions_survives_corrupt_field(self) -> None:
        """Regression (library-review R1 representative repro,
        2026-08-20): one corrupt Redis hash field must degrade per
        Principle 15, not crash recall with JSONDecodeError."""
        client = _StubClient({"decisions": "{corrupt json", "updated_at": "2026-08-20T00:00:00"})
        memory = SimpleNamespace(use_mock=False, _client=client)
        index = ConversationSummaryIndex(memory)
        result = index.recall_decisions("auth")
        assert result == []
