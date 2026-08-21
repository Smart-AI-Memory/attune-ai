"""One legacy list-shaped key must not block every promotion (class I-4).

``StagedPattern.from_dict(json.loads(raw))`` parses fine on a stored
LIST and then raises ``TypeError`` from inside ``from_dict`` — past a
caller whose except tuple lists only ``JSONDecodeError``. Because the
listing backs promotion, one such key blocked ALL promotions, which is a
Principle-15 violation: the memory layer degrades, it never blocks.

Exercised through the real mixin against a store holding real JSON — the
defect is about what a reconstructor does to bytes that actually came
back from storage, so a mocked parser could not see it (class-M ruling).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import warnings

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from attune.redis_memory_coordination import ConflictNegotiationMixin
    from attune.redis_memory_patterns import PatternStagingMixin

from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    ConflictContext,
    StagedPattern,
)


def _good_pattern() -> StagedPattern:
    return StagedPattern(
        pattern_id="p-good",
        agent_id="agent-1",
        pattern_type="insight",
        name="good pattern",
        description="a readable staged record",
    )


class _Staging(PatternStagingMixin):
    PREFIX_STAGED = "staged:"

    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def _keys(self, pattern: str) -> list[str]:
        return sorted(self._store)

    def _get(self, key: str) -> str | None:
        return self._store.get(key)

    def _delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None


class _Conflicts(ConflictNegotiationMixin):
    PREFIX_CONFLICT = "conflict:"

    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def _get(self, key: str) -> str | None:
        return self._store.get(key)


@pytest.fixture
def creds() -> AgentCredentials:
    return AgentCredentials(agent_id="a1", tier=AccessTier.VALIDATOR)


def test_legacy_list_key_does_not_block_the_listing(creds) -> None:
    """The good record must survive a list-shaped sibling."""
    good = _good_pattern()
    staging = _Staging(
        {
            "staged:p-good": json.dumps(good.to_dict()),
            # The legacy shape: valid JSON, not a mapping.
            "staged:p-legacy": json.dumps(["p-legacy", "old list form"]),
        }
    )

    out = staging.list_staged_patterns(creds)

    assert [p.pattern_id for p in out] == ["p-good"], (
        "a legacy list-shaped key blocked the listing that backs every "
        "promotion (P15: degrade, never block)"
    )


def test_single_legacy_record_reads_as_absent(creds) -> None:
    """A single unreadable record is None, not an exception."""
    staging = _Staging({"staged:p-legacy": json.dumps(["not", "a", "mapping"])})
    assert staging.get_staged_pattern("p-legacy", creds) is None


def test_unparseable_bytes_read_as_absent(creds) -> None:
    """Not-JSON-at-all degrades the same way."""
    staging = _Staging({"staged:p-broken": "{ this is not json"})
    assert staging.get_staged_pattern("p-broken", creds) is None


def test_promotion_of_a_legacy_record_degrades(creds) -> None:
    """Promotion returns None rather than raising, and deletes nothing."""
    store = {"staged:p-legacy": json.dumps(["not", "a", "mapping"])}
    staging = _Staging(store)
    assert staging.promote_pattern("p-legacy", creds) is None
    assert "staged:p-legacy" in store, "unreadable record was deleted on a failed promote"


def test_good_record_still_round_trips(creds) -> None:
    """The guard must not break the normal path."""
    good = _good_pattern()
    staging = _Staging({"staged:p-good": json.dumps(good.to_dict())})
    got = staging.get_staged_pattern("p-good", creds)
    assert got is not None
    assert got.pattern_id == "p-good"
    assert got.name == "good pattern"


def test_conflict_context_legacy_record_degrades(creds) -> None:
    """The same class in the coordination twin."""
    conflicts = _Conflicts({"conflict:c-legacy": json.dumps(["old", "form"])})
    assert conflicts.get_conflict_context("c-legacy", creds) is None


def test_conflict_context_good_record_round_trips(creds) -> None:
    ctx = ConflictContext(
        conflict_id="c1",
        positions={"a": "x"},
        interests={"a": ["y"]},
    )
    conflicts = _Conflicts({"conflict:c1": json.dumps(ctx.to_dict())})
    got = conflicts.get_conflict_context("c1", creds)
    assert got is not None
    assert got.conflict_id == "c1"
