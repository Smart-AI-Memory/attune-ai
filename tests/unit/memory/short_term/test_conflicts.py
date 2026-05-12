"""Tests for `attune.memory.short_term.conflicts.ConflictNegotiation`.

Strategy: real `BaseOperations(use_mock=True)` host (the
established convention in `tests/unit/memory/test_short_term.py`)
composed with `ConflictNegotiation`. Real serialization via
`ConflictContext.to_dict()` / `.from_dict()`. No mock of the
storage backend — the mock-mode BaseOperations is itself a real
in-memory store, faithful to production semantics without
requiring a live Redis.

Covers:
- `create_conflict_context`: happy paths (with/without BATNA),
  empty/whitespace conflict_id validation, positions/interests
  type validation, permission gating at CONTRIBUTOR threshold,
  key prefix correctness, TTL applied.
- `get_conflict_context`: hit, miss, empty-id validation,
  round-trip through serialization.
- `resolve_conflict`: permission gating at VALIDATOR threshold,
  missing-context returns False, happy path mutates resolved
  state + resolution string, can_validate ordering vs id
  validation.
- `list_active_conflicts`: empty store, filters out resolved
  conflicts, returns all unresolved.

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
    TTLStrategy,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_ops() -> BaseOperations:
    """Real BaseOperations in mock mode — in-memory storage."""
    return BaseOperations(use_mock=True)


@pytest.fixture
def negotiation(base_ops: BaseOperations) -> ConflictNegotiation:
    return ConflictNegotiation(base_ops)


@pytest.fixture
def contributor_creds() -> AgentCredentials:
    return AgentCredentials("contributor_agent", AccessTier.CONTRIBUTOR)


@pytest.fixture
def validator_creds() -> AgentCredentials:
    return AgentCredentials("validator_agent", AccessTier.VALIDATOR)


@pytest.fixture
def observer_creds() -> AgentCredentials:
    return AgentCredentials("observer_agent", AccessTier.OBSERVER)


@pytest.fixture
def steward_creds() -> AgentCredentials:
    return AgentCredentials("steward_agent", AccessTier.STEWARD)


# ---------------------------------------------------------------------------
# create_conflict_context
# ---------------------------------------------------------------------------


class TestCreateConflictContext:
    def test_happy_path_no_batna(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        context = negotiation.create_conflict_context(
            "c1",
            positions={"a1": "Redis", "a2": "SQLite"},
            interests={"a1": ["speed"], "a2": ["simplicity"]},
            credentials=contributor_creds,
        )
        assert isinstance(context, ConflictContext)
        assert context.conflict_id == "c1"
        assert context.positions == {"a1": "Redis", "a2": "SQLite"}
        assert context.interests == {"a1": ["speed"], "a2": ["simplicity"]}
        assert context.batna is None
        assert context.resolved is False
        assert context.resolution is None

    def test_happy_path_with_batna(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        context = negotiation.create_conflict_context(
            "c1",
            positions={"a1": "Redis"},
            interests={"a1": ["speed"]},
            credentials=contributor_creds,
            batna="file-based storage",
        )
        assert context.batna == "file-based storage"

    def test_higher_tier_can_create(
        self,
        negotiation: ConflictNegotiation,
        validator_creds: AgentCredentials,
        steward_creds: AgentCredentials,
    ) -> None:
        # VALIDATOR and STEWARD both satisfy can_stage().
        c1 = negotiation.create_conflict_context("c-validator", {}, {}, credentials=validator_creds)
        c2 = negotiation.create_conflict_context("c-steward", {}, {}, credentials=steward_creds)
        assert c1.conflict_id == "c-validator"
        assert c2.conflict_id == "c-steward"

    def test_observer_blocked(
        self,
        negotiation: ConflictNegotiation,
        observer_creds: AgentCredentials,
    ) -> None:
        with pytest.raises(PermissionError, match="CONTRIBUTOR tier or higher"):
            negotiation.create_conflict_context("c1", {}, {}, credentials=observer_creds)

    @pytest.mark.parametrize("bad_id", ["", "   ", "\t", "\n"])
    def test_empty_or_whitespace_id_raises(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.create_conflict_context(bad_id, {}, {}, credentials=contributor_creds)

    @pytest.mark.parametrize("bad_positions", [[], "not-a-dict", 42, None, ("a", "b")])
    def test_positions_must_be_dict(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        bad_positions: object,
    ) -> None:
        with pytest.raises(TypeError, match="positions must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions=bad_positions,  # type: ignore[arg-type]
                interests={},
                credentials=contributor_creds,
            )

    @pytest.mark.parametrize("bad_interests", [[], "not-a-dict", 42, None, ("a", "b")])
    def test_interests_must_be_dict(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        bad_interests: object,
    ) -> None:
        with pytest.raises(TypeError, match="interests must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions={},
                interests=bad_interests,  # type: ignore[arg-type]
                credentials=contributor_creds,
            )

    def test_id_validation_runs_before_type_validation(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        # Both an empty id AND a bad positions type → ValueError
        # surfaces first (line ordering in source). Locks down
        # the documented error order so future refactors don't
        # silently flip it.
        with pytest.raises(ValueError, match="conflict_id"):
            negotiation.create_conflict_context(
                "",
                positions="bad",  # type: ignore[arg-type]
                interests={},
                credentials=contributor_creds,
            )

    def test_type_validation_runs_before_permission_check(
        self,
        negotiation: ConflictNegotiation,
        observer_creds: AgentCredentials,
    ) -> None:
        # Even with insufficient tier, the TypeError fires first
        # because the type checks are evaluated before
        # can_stage(). Documents the source line order.
        with pytest.raises(TypeError, match="positions must be dict"):
            negotiation.create_conflict_context(
                "c1",
                positions="bad",  # type: ignore[arg-type]
                interests={},
                credentials=observer_creds,
            )

    def test_stored_under_prefix_with_ttl(
        self,
        negotiation: ConflictNegotiation,
        base_ops: BaseOperations,
        contributor_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1", {"a": "x"}, {"a": ["y"]}, credentials=contributor_creds
        )
        # Key uses PREFIX_CONFLICT + id.
        expected_key = f"{ConflictNegotiation.PREFIX_CONFLICT}c1"
        raw = base_ops._get(expected_key)
        assert raw is not None
        # Stored as JSON, round-trips through to_dict/from_dict.
        roundtrip = ConflictContext.from_dict(json.loads(raw))
        assert roundtrip.conflict_id == "c1"
        assert roundtrip.positions == {"a": "x"}

    def test_logs_creation_event(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        # `structlog.testing.capture_logs()` is the canonical
        # capture primitive — bypasses I/O entirely and reads
        # structured events directly. Earlier versions used
        # `capsys` to read stdout, but structlog's WriteLogger
        # caches `sys.stdout` at logger-creation time, so
        # pytest's stdout monkey-patching (especially under
        # `pytest-xdist` on Linux) intermittently sees empty
        # output. The event record path is environment-stable.
        from structlog.testing import capture_logs

        with capture_logs() as cap:
            negotiation.create_conflict_context(
                "c1",
                {"a1": "x", "a2": "y"},
                {},
                credentials=contributor_creds,
                batna="fallback",
            )
        assert any(e.get("event") == "conflict_context_created" for e in cap)


# ---------------------------------------------------------------------------
# get_conflict_context
# ---------------------------------------------------------------------------


class TestGetConflictContext:
    def test_returns_context_after_create(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1",
            {"a1": "Redis"},
            {"a1": ["speed"]},
            credentials=contributor_creds,
            batna="fallback",
        )
        retrieved = negotiation.get_conflict_context("c1", contributor_creds)
        assert retrieved is not None
        assert retrieved.conflict_id == "c1"
        assert retrieved.positions == {"a1": "Redis"}
        assert retrieved.interests == {"a1": ["speed"]}
        assert retrieved.batna == "fallback"

    def test_returns_none_for_missing_id(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        assert negotiation.get_conflict_context("never-created", contributor_creds) is None

    @pytest.mark.parametrize("bad_id", ["", "   ", "\t"])
    def test_empty_or_whitespace_id_raises(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        bad_id: str,
    ) -> None:
        with pytest.raises(ValueError, match="conflict_id cannot be empty"):
            negotiation.get_conflict_context(bad_id, contributor_creds)

    def test_observer_can_read(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        observer_creds: AgentCredentials,
    ) -> None:
        # Observer was blocked from create, but can read — the
        # docstring says "Any tier can read."
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        context = negotiation.get_conflict_context("c1", observer_creds)
        assert context is not None


# ---------------------------------------------------------------------------
# resolve_conflict
# ---------------------------------------------------------------------------


class TestResolveConflict:
    def test_happy_path_marks_resolved(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        ok = negotiation.resolve_conflict("c1", "Chose Redis for speed", validator_creds)
        assert ok is True
        retrieved = negotiation.get_conflict_context("c1", validator_creds)
        assert retrieved is not None
        assert retrieved.resolved is True
        assert retrieved.resolution == "Chose Redis for speed"

    def test_returns_false_when_conflict_not_found(
        self,
        negotiation: ConflictNegotiation,
        validator_creds: AgentCredentials,
    ) -> None:
        # The permission check passes (validator can validate);
        # the conflict lookup misses, so return False rather than
        # raise.
        assert negotiation.resolve_conflict("does-not-exist", "n/a", validator_creds) is False

    def test_contributor_blocked(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        # Contributor can create but not validate → resolve must
        # raise PermissionError.
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        with pytest.raises(PermissionError, match="VALIDATOR tier or higher"):
            negotiation.resolve_conflict("c1", "x", contributor_creds)

    def test_observer_blocked(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        observer_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        with pytest.raises(PermissionError, match="VALIDATOR tier or higher"):
            negotiation.resolve_conflict("c1", "x", observer_creds)

    def test_steward_can_resolve(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        steward_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        assert negotiation.resolve_conflict("c1", "stewarded", steward_creds) is True

    def test_permission_check_runs_before_lookup(
        self,
        negotiation: ConflictNegotiation,
        observer_creds: AgentCredentials,
    ) -> None:
        # Conflict doesn't exist + insufficient credentials.
        # Permission check fires first → PermissionError, not
        # `return False` from missing-context branch.
        with pytest.raises(PermissionError):
            negotiation.resolve_conflict("never-existed", "x", observer_creds)

    def test_resolution_persists_across_reads(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1",
            {"a1": "x"},
            {"a1": ["y"]},
            credentials=contributor_creds,
            batna="b",
        )
        negotiation.resolve_conflict("c1", "done", validator_creds)
        # Two fresh reads see the same resolved state.
        c1 = negotiation.get_conflict_context("c1", contributor_creds)
        c2 = negotiation.get_conflict_context("c1", validator_creds)
        assert c1 is not None and c2 is not None
        assert c1.resolved is True and c2.resolved is True
        assert c1.batna == "b" and c2.batna == "b"

    def test_logs_resolution_event(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        # See `test_logs_creation_event` for why `capture_logs`
        # is preferred over `capsys` here.
        from structlog.testing import capture_logs

        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        with capture_logs() as cap:
            negotiation.resolve_conflict("c1", "done", validator_creds)
        assert any(e.get("event") == "conflict_resolved" for e in cap)


# ---------------------------------------------------------------------------
# list_active_conflicts
# ---------------------------------------------------------------------------


class TestListActiveConflicts:
    def test_empty_store_returns_empty(
        self,
        negotiation: ConflictNegotiation,
        observer_creds: AgentCredentials,
    ) -> None:
        assert negotiation.list_active_conflicts(observer_creds) == []

    def test_lists_only_unresolved(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        # 3 created, 1 resolved → 2 active.
        for cid in ("c1", "c2", "c3"):
            negotiation.create_conflict_context(cid, {}, {}, credentials=contributor_creds)
        negotiation.resolve_conflict("c2", "done", validator_creds)

        active = negotiation.list_active_conflicts(contributor_creds)
        active_ids = sorted(c.conflict_id for c in active)
        assert active_ids == ["c1", "c3"]

    def test_observer_can_list(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        observer_creds: AgentCredentials,
    ) -> None:
        # Docstring says "any tier can read"
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        assert len(negotiation.list_active_conflicts(observer_creds)) == 1

    def test_returns_full_context_not_just_ids(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context(
            "c1",
            {"a1": "x"},
            {"a1": ["y"]},
            credentials=contributor_creds,
            batna="z",
        )
        active = negotiation.list_active_conflicts(contributor_creds)
        assert len(active) == 1
        ctx = active[0]
        assert ctx.positions == {"a1": "x"}
        assert ctx.batna == "z"

    def test_no_active_returned_when_all_resolved(
        self,
        negotiation: ConflictNegotiation,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        negotiation.create_conflict_context("c1", {}, {}, credentials=contributor_creds)
        negotiation.resolve_conflict("c1", "done", validator_creds)
        assert negotiation.list_active_conflicts(contributor_creds) == []

    def test_skips_keys_with_empty_value(
        self,
        negotiation: ConflictNegotiation,
        base_ops: BaseOperations,
        contributor_creds: AgentCredentials,
    ) -> None:
        # Source line 267: `if raw:` skips falsy values.
        # Plant an empty-string value at a prefix-matching key to
        # exercise the skip branch.
        negotiation.create_conflict_context("real", {}, {}, credentials=contributor_creds)
        base_ops._set(
            f"{ConflictNegotiation.PREFIX_CONFLICT}sentinel",
            "",
            TTLStrategy.CONFLICT_CONTEXT.value,
        )

        active = negotiation.list_active_conflicts(contributor_creds)
        assert [c.conflict_id for c in active] == ["real"]


# ---------------------------------------------------------------------------
# Class attribute + init invariants
# ---------------------------------------------------------------------------


class TestInvariants:
    def test_prefix_constant_unchanged(self) -> None:
        # If this changes, every existing stored conflict key is
        # orphaned. Locks the constant against accidental rename.
        assert ConflictNegotiation.PREFIX_CONFLICT == "empathy:conflict:"

    def test_init_stores_base(self, base_ops: BaseOperations) -> None:
        n = ConflictNegotiation(base_ops)
        assert n._base is base_ops
