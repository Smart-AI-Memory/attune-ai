"""Behavioral tests for PatternStaging (src/attune/memory/short_term/patterns.py).

Drives the pattern staging lifecycle through the RedisShortTermMemory
facade in built-in mock mode (no Redis, no network), targeting the
guard clauses and code paths Codecov shows as unexercised on main:
type validation on stage, permission checks on stage/promote/reject,
empty-id validation on get, the promote success/not-found paths, and
count_staged. Each test asserts observable behavior through the
facade's public contract, matching the house style in test_facade.py.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.memory.short_term import RedisShortTermMemory
from attune.memory.types import AccessTier, AgentCredentials, StagedPattern


@pytest.fixture
def memory() -> RedisShortTermMemory:
    """Facade in built-in mock mode (no Redis required)."""
    mem = RedisShortTermMemory(use_mock=True)
    yield mem
    mem.close()


def _creds(agent_id: str = "agent_1", tier: AccessTier = AccessTier.CONTRIBUTOR):
    return AgentCredentials(agent_id, tier)


def _pattern(pattern_id: str = "pat_1", agent_id: str = "agent_1") -> StagedPattern:
    return StagedPattern(
        pattern_id=pattern_id,
        agent_id=agent_id,
        pattern_type="debugging",
        name="null-check",
        description="Guard against None before attribute access",
        confidence=0.8,
    )


class TestStagePatternValidation:
    """stage_pattern guards type and tier before writing."""

    def test_rejects_non_staged_pattern_type(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)

        with pytest.raises(TypeError, match="must be StagedPattern"):
            memory.stage_pattern({"not": "a pattern"}, contributor)

    def test_observer_tier_cannot_stage(self, memory):
        observer = _creds("observer", AccessTier.OBSERVER)

        with pytest.raises(PermissionError, match="cannot stage patterns"):
            memory.stage_pattern(_pattern("pat_denied"), observer)

        # Confirm nothing was written despite the attempted stage.
        validator = _creds("validator", AccessTier.VALIDATOR)
        assert memory.get_staged_pattern("pat_denied", validator) is None


class TestGetStagedPatternValidation:
    """get_staged_pattern rejects empty/whitespace pattern_id before lookup."""

    def test_empty_pattern_id_raises(self, memory):
        contributor = _creds()

        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            memory.get_staged_pattern("", contributor)

    def test_whitespace_pattern_id_raises(self, memory):
        contributor = _creds()

        with pytest.raises(ValueError, match="pattern_id cannot be empty"):
            memory.get_staged_pattern("   ", contributor)


class TestPromotePattern:
    """promote_pattern enforces validator tier, removes on success, no-ops on miss."""

    def test_promote_requires_validator_tier(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        memory.stage_pattern(_pattern("pat_guarded"), contributor)

        with pytest.raises(PermissionError, match="cannot promote patterns"):
            memory.promote_pattern("pat_guarded", contributor)

    def test_promote_removes_pattern_and_returns_it(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        validator = _creds("validator", AccessTier.VALIDATOR)
        memory.stage_pattern(_pattern("pat_promote", agent_id="contrib"), contributor)

        promoted = memory.promote_pattern("pat_promote", validator)

        assert promoted is not None
        assert promoted.pattern_id == "pat_promote"
        assert memory.get_staged_pattern("pat_promote", validator) is None

    def test_promote_missing_pattern_returns_none(self, memory):
        validator = _creds("validator", AccessTier.VALIDATOR)

        assert memory.promote_pattern("does_not_exist", validator) is None


class TestListStagedPatterns:
    """list_staged_patterns returns every currently-staged pattern."""

    def test_list_returns_all_staged_patterns(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        memory.stage_pattern(_pattern("pat_x", agent_id="contrib"), contributor)
        memory.stage_pattern(_pattern("pat_y", agent_id="contrib"), contributor)

        listed = memory.list_staged_patterns(contributor)

        assert {p.pattern_id for p in listed} == {"pat_x", "pat_y"}

    def test_list_empty_when_nothing_staged(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)

        assert memory.list_staged_patterns(contributor) == []


class TestCountStaged:
    """count_staged reflects the number of staged (unpromoted) patterns."""

    def test_count_starts_at_zero(self, memory):
        assert memory._patterns.count_staged() == 0

    def test_count_reflects_stage_and_promote(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        validator = _creds("validator", AccessTier.VALIDATOR)

        memory.stage_pattern(_pattern("pat_a", agent_id="contrib"), contributor)
        memory.stage_pattern(_pattern("pat_b", agent_id="contrib"), contributor)
        assert memory._patterns.count_staged() == 2

        memory.promote_pattern("pat_a", validator)
        assert memory._patterns.count_staged() == 1
