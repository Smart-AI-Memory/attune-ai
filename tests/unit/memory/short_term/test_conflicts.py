"""Tests for `attune.memory.short_term.conflicts.ConflictNegotiation`.

Strategy: real `BaseOperations(use_mock=True)` instance for storage.
The mock path is an in-memory dict, so we exercise the real
serialization, TTL, and key-scan paths end-to-end without any
network or Redis dependency. No mocking of `_get`/`_set`/`_keys`
— if those drift, tests catch it.

Covers:
- Public API: __init__, create_conflict_context,
  get_conflict_context, resolve_conflict, list_active_conflicts.
- Permission paths: stage (CONTRIBUTOR+), validate (VALIDATOR+),
  read (any tier).
- Input validation: empty/whitespace conflict_id, non-dict
  positions/interests.
- Storage shape: persisted under PREFIX_CONFLICT, JSON-encoded,
  round-trips via ConflictContext.to_dict / from_dict.
- list_active_conflicts: filters resolved out, returns empty
  when nothing is stored, handles other PREFIX_CONFLICT-keyed
  entries that don't belong (defensive — _keys returns only
  the conflict prefix so this is just round-trip).

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.memory.short_term.base import BaseOperations
from attune.memory.short_term.conflicts import ConflictNegotiation
from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    ConflictContext,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base() -> BaseOperations:
    """In-memory BaseOperations — no Redis required."""
    return BaseOperations(use_mock=True)


@pytest.fixture
def negotiation(base: BaseOperations) -> ConflictNegotiation:
    return ConflictNegotiation(base)


@pytest.fixture
def observer() -> AgentCredentials:
    return AgentCredentials("observer_1", AccessTier.OBSERVER)


@pytest.fixture
def contributor() -> AgentCredentials:
    return AgentCredentials("contributor_1", AccessTier.CONTRIBUTOR)


@pytest.fixture
def validator() -> AgentCredentials:
    return AgentCredentials("validator_1", AccessTier.VALIDATOR)


@pytest.fixture
def steward() -> AgentCredentials:
    return AgentCredentials("steward_1", AccessTier.STEWARD)


def _positions() -> dict[str, str]:
    return {"agent_a": "Use Redis", "agent_b": "Use SQLite"}


def _interests() -> dict[str, list[str]]:
    return {"agent_a": ["speed", "scale"], "agent_b": ["simplicity"]}


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_stores_base_reference(self, base: BaseOperations) -> None:
        negotiation = ConflictNegotiation(base)
        assert negotiation._base is base

    def test_prefix_constant_matches_key_layout(self) -> None:
        # The class-level prefix must keep parity with what
        # BaseOperations namespaces conflicts under, so other
        # callers scanning the global namespace see the same set.
        assert ConflictNegotiation.PREFIX_CONFLICT == "empathy:conflict:"
        assert ConflictNegotiation.PREFIX_CONFLICT == BaseOperations.PREFIX_CONFLICT


# ---------------------------------------------------------------------------
# create_conflict_context — validation
# ---------------------------------------------------------------------------


class TestCreateValidation:
    def test_empty_id_raises_value_error(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.create_conflict_context(
                "", positions=_positions(), interests=_interests(), credentials=contributor
            )

    def test_whitespace_id_raises_value_error(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.create_conflict_context(
                "   ",
                positions=_positions(),
                interests=_interests(),
                credentials=contributor,
            )

    def test_non_dict_positions_raises_type_error(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        with pytest.raises(TypeError, match="positions must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions=["agent_a", "Redis"],  # type: ignore[arg-type]
                interests=_interests(),
                credentials=contributor,
            )

    def test_non_dict_interests_raises_type_error(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        with pytest.raises(TypeError, match="interests must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions=_positions(),
                interests="agent_a wants speed",  # type: ignore[arg-type]
                credentials=contributor,
            )

    def test_observer_cannot_create(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        with pytest.raises(PermissionError, match="CONTRIBUTOR tier or higher"):
            negotiation.create_conflict_context(
                "c1", positions=_positions(), interests=_interests(), credentials=observer
            )

    def test_validation_order_id_before_types(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        # Empty id is checked before positions/interests type, so
        # an empty id with bad positions still surfaces as ValueError.
        # Locks in the order so callers can rely on it.
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.create_conflict_context(
                "",
                positions="not a dict",  # type: ignore[arg-type]
                interests=_interests(),
                credentials=contributor,
            )

    def test_validation_order_types_before_permissions(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        # Type errors fire before permission check, so an Observer
        # with non-dict positions gets TypeError, not PermissionError.
        with pytest.raises(TypeError, match="positions must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions="bad",  # type: ignore[arg-type]
                interests=_interests(),
                credentials=observer,
            )


# ---------------------------------------------------------------------------
# create_conflict_context — happy path + persistence
# ---------------------------------------------------------------------------


class TestCreatePersistence:
    def test_returns_context_with_inputs(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        context = negotiation.create_conflict_context(
            "c1",
            positions=_positions(),
            interests=_interests(),
            credentials=contributor,
        )
        assert context.conflict_id == "c1"
        assert context.positions == _positions()
        assert context.interests == _interests()
        assert context.batna is None
        assert context.resolved is False
        assert context.resolution is None

    def test_batna_is_stored(
        self, negotiation: ConflictNegotiation, contributor: AgentCredentials
    ) -> None:
        context = negotiation.create_conflict_context(
            "c1",
            positions=_positions(),
            interests=_interests(),
            credentials=contributor,
            batna="Use file-based storage",
        )
        assert context.batna == "Use file-based storage"

    def test_persists_under_prefix_conflict(
        self,
        base: BaseOperations,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        raw = base._get("empathy:conflict:c1")
        assert raw is not None
        payload = json.loads(raw)
        assert payload["conflict_id"] == "c1"
        assert payload["positions"] == _positions()
        assert payload["resolved"] is False

    def test_validator_and_steward_can_create(
        self,
        negotiation: ConflictNegotiation,
        validator: AgentCredentials,
        steward: AgentCredentials,
    ) -> None:
        # Both higher tiers also satisfy can_stage().
        negotiation.create_conflict_context(
            "by_validator", positions=_positions(), interests=_interests(), credentials=validator
        )
        negotiation.create_conflict_context(
            "by_steward", positions=_positions(), interests=_interests(), credentials=steward
        )
        assert negotiation.get_conflict_context("by_validator", validator) is not None
        assert negotiation.get_conflict_context("by_steward", steward) is not None


# ---------------------------------------------------------------------------
# get_conflict_context
# ---------------------------------------------------------------------------


class TestGetConflictContext:
    def test_missing_returns_none(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        assert negotiation.get_conflict_context("never_created", observer) is None

    def test_empty_id_raises_value_error(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.get_conflict_context("", observer)

    def test_whitespace_id_raises_value_error(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.get_conflict_context("\t  ", observer)

    def test_round_trip_preserves_fields(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        observer: AgentCredentials,
    ) -> None:
        original = negotiation.create_conflict_context(
            "round_trip",
            positions=_positions(),
            interests=_interests(),
            credentials=contributor,
            batna="fallback",
        )
        # Any tier can read.
        fetched = negotiation.get_conflict_context("round_trip", observer)
        assert fetched is not None
        assert fetched.conflict_id == original.conflict_id
        assert fetched.positions == original.positions
        assert fetched.interests == original.interests
        assert fetched.batna == original.batna
        assert fetched.resolved is False
        assert fetched.resolution is None


# ---------------------------------------------------------------------------
# resolve_conflict
# ---------------------------------------------------------------------------


class TestResolveConflict:
    def test_observer_cannot_resolve(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        observer: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        with pytest.raises(PermissionError, match="VALIDATOR tier or higher"):
            negotiation.resolve_conflict("c1", "answer", observer)

    def test_contributor_cannot_resolve(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
    ) -> None:
        # Contributors can create but not resolve — locks in the
        # separation of stage vs validate access.
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        with pytest.raises(PermissionError, match="VALIDATOR tier or higher"):
            negotiation.resolve_conflict("c1", "answer", contributor)

    def test_permission_check_runs_before_existence_check(
        self,
        negotiation: ConflictNegotiation,
        observer: AgentCredentials,
    ) -> None:
        # No conflict stored; observer gets PermissionError, not False.
        # Documents the ordering: permission first, lookup second.
        with pytest.raises(PermissionError, match="VALIDATOR tier or higher"):
            negotiation.resolve_conflict("never_created", "answer", observer)

    def test_missing_conflict_returns_false(
        self, negotiation: ConflictNegotiation, validator: AgentCredentials
    ) -> None:
        assert negotiation.resolve_conflict("never_created", "answer", validator) is False

    def test_resolves_and_persists(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        validator: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        assert negotiation.resolve_conflict("c1", "Chose Redis", validator) is True

        fetched = negotiation.get_conflict_context("c1", validator)
        assert fetched is not None
        assert fetched.resolved is True
        assert fetched.resolution == "Chose Redis"

    def test_resolve_propagates_id_validation(
        self, negotiation: ConflictNegotiation, validator: AgentCredentials
    ) -> None:
        # resolve_conflict delegates id validation to
        # get_conflict_context. Empty id should still raise.
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.resolve_conflict("", "answer", validator)

    def test_steward_can_resolve(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        steward: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "by_contrib",
            positions=_positions(),
            interests=_interests(),
            credentials=contributor,
        )
        assert negotiation.resolve_conflict("by_contrib", "Chose X", steward) is True


# ---------------------------------------------------------------------------
# list_active_conflicts
# ---------------------------------------------------------------------------


class TestListActiveConflicts:
    def test_empty_when_nothing_stored(
        self, negotiation: ConflictNegotiation, observer: AgentCredentials
    ) -> None:
        assert negotiation.list_active_conflicts(observer) == []

    def test_returns_only_unresolved(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        validator: AgentCredentials,
        observer: AgentCredentials,
    ) -> None:
        for cid in ("c1", "c2", "c3"):
            negotiation.create_conflict_context(
                cid,
                positions=_positions(),
                interests=_interests(),
                credentials=contributor,
            )
        # Resolve c2 only.
        negotiation.resolve_conflict("c2", "answer", validator)

        active = negotiation.list_active_conflicts(observer)
        active_ids = sorted(c.conflict_id for c in active)
        assert active_ids == ["c1", "c3"]
        # And every returned entry is genuinely unresolved.
        assert all(c.resolved is False for c in active)

    def test_empty_when_all_resolved(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        validator: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        negotiation.resolve_conflict("c1", "answer", validator)
        assert negotiation.list_active_conflicts(validator) == []

    def test_skips_keys_with_falsy_raw(
        self,
        base: BaseOperations,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        validator: AgentCredentials,
    ) -> None:
        # A conflict-prefixed key whose value is the empty string
        # is silently skipped by `if raw:` (line ~267). Documents
        # the resilience: list_active_conflicts does not crash on
        # an empty/None entry, it just drops it.
        negotiation.create_conflict_context(
            "c1", positions=_positions(), interests=_interests(), credentials=contributor
        )
        base._set("empathy:conflict:empty_value", "", ttl=60)

        active = negotiation.list_active_conflicts(validator)
        assert [c.conflict_id for c in active] == ["c1"]


# ---------------------------------------------------------------------------
# Cross-method invariants
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_create_then_resolve_then_list_then_get(
        self,
        negotiation: ConflictNegotiation,
        contributor: AgentCredentials,
        validator: AgentCredentials,
    ) -> None:
        # Full lifecycle in one path.
        created = negotiation.create_conflict_context(
            "lifecycle",
            positions=_positions(),
            interests=_interests(),
            credentials=contributor,
            batna="fallback",
        )
        assert isinstance(created, ConflictContext)

        # Not yet resolved → appears in list.
        active_before = negotiation.list_active_conflicts(validator)
        assert any(c.conflict_id == "lifecycle" for c in active_before)

        # Resolve it.
        assert negotiation.resolve_conflict("lifecycle", "go", validator) is True

        # No longer in active list.
        active_after = negotiation.list_active_conflicts(validator)
        assert not any(c.conflict_id == "lifecycle" for c in active_after)

        # But still fetchable, with resolution preserved.
        fetched = negotiation.get_conflict_context("lifecycle", validator)
        assert fetched is not None
        assert fetched.resolved is True
        assert fetched.resolution == "go"
        assert fetched.batna == "fallback"
