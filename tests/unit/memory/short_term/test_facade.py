"""Behavioral tests for the RedisShortTermMemory facade delegation surface.

Drives the facade in built-in mock mode (no Redis, no network) and
exercises the delegation methods Codecov shows as unexercised on main:
client/metrics properties, pattern rejection, conflict negotiation,
coordination signals, collaboration sessions, cross-session degradation,
cache stats, the testing-support accessors, and the _keys/_delete
internals. Each test asserts observable behavior through the facade's
public contract, not implementation details.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.memory.short_term import RedisShortTermMemory
from attune.memory.types import (
    AccessTier,
    AgentCredentials,
    RedisMetrics,
    StagedPattern,
)


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


class TestProperties:
    """Facade properties delegate to BaseOperations."""

    def test_client_is_none_in_mock_mode(self, memory):
        assert memory.client is None

    def test_metrics_property_returns_metrics_instance(self, memory):
        assert isinstance(memory.metrics, RedisMetrics)

    def test_config_property_exposes_mock_flag(self, memory):
        assert memory._config.use_mock is True

    def test_internal_metrics_alias_matches_public_metrics(self, memory):
        assert memory._metrics is memory.metrics

    def test_ping_succeeds_in_mock_mode(self, memory):
        assert memory.ping() is True


class TestPatternRejection:
    """reject_pattern removes a staged pattern for validator-tier agents."""

    def test_reject_removes_staged_pattern(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        validator = _creds("validator", AccessTier.VALIDATOR)
        assert memory.stage_pattern(_pattern("pat_reject"), contributor) is True

        assert memory.reject_pattern("pat_reject", validator, reason="too vague") is True
        assert memory.get_staged_pattern("pat_reject", validator) is None

    def test_reject_requires_validator_tier(self, memory):
        contributor = _creds("contrib", AccessTier.CONTRIBUTOR)
        memory.stage_pattern(_pattern("pat_guarded"), contributor)

        with pytest.raises(PermissionError):
            memory.reject_pattern("pat_guarded", contributor)


class TestConflictNegotiation:
    """Conflict context lifecycle round-trips through the facade."""

    def test_create_and_get_conflict_context(self, memory):
        contributor = _creds("a1", AccessTier.CONTRIBUTOR)
        created = memory.create_conflict_context(
            "conflict_1",
            positions={"a1": "Redis", "a2": "SQLite"},
            interests={"a1": ["speed"], "a2": ["simplicity"]},
            credentials=contributor,
            batna="file-based storage",
        )
        assert created.conflict_id == "conflict_1"

        fetched = memory.get_conflict_context("conflict_1", contributor)
        assert fetched is not None
        assert fetched.positions == {"a1": "Redis", "a2": "SQLite"}
        assert fetched.batna == "file-based storage"

    def test_resolve_conflict_removes_it_from_active_list(self, memory):
        contributor = _creds("a1", AccessTier.CONTRIBUTOR)
        validator = _creds("v1", AccessTier.VALIDATOR)
        memory.create_conflict_context(
            "conflict_2",
            positions={"a1": "tabs", "a2": "spaces"},
            interests={"a1": ["speed"], "a2": ["style"]},
            credentials=contributor,
        )
        assert len(memory.list_active_conflicts(contributor)) == 1

        assert memory.resolve_conflict("conflict_2", "spaces won", validator) is True
        assert memory.list_active_conflicts(contributor) == []

        resolved = memory.get_conflict_context("conflict_2", contributor)
        assert resolved.resolved is True
        assert resolved.resolution == "spaces won"


class TestCoordinationSignals:
    """send_signal / receive_signals round-trip through mock storage."""

    def test_targeted_signal_round_trip(self, memory):
        sender = _creds("sender", AccessTier.CONTRIBUTOR)
        receiver = _creds("receiver", AccessTier.CONTRIBUTOR)
        assert memory.send_signal("task_done", {"task": 1}, sender, target_agent="receiver") is True

        signals = memory.receive_signals(receiver)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "task_done"
        assert signals[0]["from_agent"] == "sender"
        assert signals[0]["to_agent"] == "receiver"
        assert signals[0]["data"] == {"task": 1}

    def test_broadcast_signal_visible_to_any_agent(self, memory):
        sender = _creds("sender", AccessTier.CONTRIBUTOR)
        bystander = _creds("bystander", AccessTier.CONTRIBUTOR)
        assert memory.send_signal("announce", "hello", sender) is True

        signals = memory.receive_signals(bystander)
        assert len(signals) == 1
        assert signals[0]["to_agent"] is None

    def test_signal_type_filter_excludes_other_targeted_types(self, memory):
        sender = _creds("sender", AccessTier.CONTRIBUTOR)
        receiver = _creds("receiver", AccessTier.CONTRIBUTOR)
        memory.send_signal("alpha", 1, sender, target_agent="receiver")

        signals = memory.receive_signals(receiver, signal_type="beta")
        assert all(s["signal_type"] != "alpha" or s["to_agent"] is None for s in signals)
        assert signals == []

    def test_observer_tier_cannot_send_signals(self, memory):
        observer = _creds("watcher", AccessTier.OBSERVER)
        with pytest.raises(PermissionError):
            memory.send_signal("nope", {}, observer)


class TestSessions:
    """Collaboration session lifecycle through the facade."""

    def test_create_join_get_lifecycle(self, memory):
        creator = _creds("creator")
        joiner = _creds("joiner")
        assert memory.create_session("s1", creator, metadata={"topic": "review"}) is True
        assert memory.join_session("s1", joiner) is True

        session = memory.get_session("s1", creator)
        assert session is not None
        assert session["participants"] == ["creator", "joiner"]
        assert session["metadata"] == {"topic": "review"}

    def test_leave_session_removes_participant(self, memory):
        creator = _creds("creator")
        joiner = _creds("joiner")
        memory.create_session("s2", creator)
        memory.join_session("s2", joiner)

        assert memory.leave_session("s2", joiner) is True
        assert memory.get_session("s2", creator)["participants"] == ["creator"]

    def test_list_sessions_returns_created_sessions(self, memory):
        creator = _creds("creator")
        memory.create_session("s3", creator)
        memory.create_session("s4", creator)

        ids = {s["session_id"] for s in memory.list_sessions(creator)}
        assert ids == {"s3", "s4"}

    def test_get_missing_session_returns_none(self, memory):
        assert memory.get_session("ghost", _creds()) is None


class TestCrossSessionDegradation:
    """Cross-session requires real Redis; mock mode degrades explicitly."""

    def test_enable_cross_session_raises_in_mock_mode(self, memory):
        with pytest.raises(ValueError, match="requires Redis"):
            memory.enable_cross_session("s1", _creds())

    def test_cross_session_available_false_in_mock_mode(self, memory):
        assert memory.cross_session_available("s1", _creds()) is False


class TestCacheOperations:
    """Local cache stats/clear are exposed on the facade."""

    def test_get_cache_stats_reports_enabled_cache(self, memory):
        stats = memory.get_cache_stats()
        assert stats["enabled"] is True

    def test_clear_cache_returns_entry_count(self, memory):
        assert memory.clear_cache() == 0


class TestTestingAccessors:
    """Backward-compat accessors delegate to the security/base modules."""

    def test_pii_scrubber_getter_and_setter_round_trip(self, memory):
        sentinel = object()
        memory._pii_scrubber = sentinel
        assert memory._pii_scrubber is sentinel
        assert memory._security._pii_scrubber is sentinel

    def test_secrets_detector_getter_and_setter_round_trip(self, memory):
        assert memory._secrets_detector is None
        sentinel = object()
        memory._secrets_detector = sentinel
        assert memory._secrets_detector is sentinel
        assert memory._security._secrets_detector is sentinel

    def test_keys_lists_stashed_working_memory(self, memory):
        creds = _creds("agent_k")
        assert memory.stash("k1", {"v": 1}, creds) is True

        keys = memory._keys(f"{RedisShortTermMemory.PREFIX_WORKING}*")
        assert len(keys) == 1
        assert keys[0].startswith(RedisShortTermMemory.PREFIX_WORKING)

        assert memory._delete(keys[0]) is True
        assert memory.retrieve("k1", creds) is None

    def test_clear_working_memory_removes_agent_data(self, memory):
        creds = _creds("agent_clear")
        memory.stash("a", 1, creds)
        memory.stash("b", 2, creds)

        cleared = memory.clear_working_memory(creds)

        assert cleared == 2
        assert memory.retrieve("a", creds) is None
        assert memory.retrieve("b", creds) is None
