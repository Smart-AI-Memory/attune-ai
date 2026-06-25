"""Comprehensive tests for coverage batch 9.

Tests for:
- attune.redis_memory (Redis short-term memory)
- attune.meta_workflows.workflow (Meta workflow execution)
- attune.meta_workflows.cli_commands.workflow_commands (CLI commands for workflows)

All external dependencies (Redis, LLM, Anthropic, etc.) are mocked.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

try:
    # Import from typer (the library that raises) rather than click.exceptions
    # — typer 0.26 vendored click and `typer.Exit` is no longer the same class
    # as `click.exceptions.Exit`. See the CLAUDE.md lesson on typer.Exit.
    from typer import Exit as ClickExit
except ImportError:
    ClickExit = SystemExit  # type: ignore[assignment,misc]


try:
    from attune.memory.types import AccessTier

    HAS_ACCESS_TIER = True
except ImportError:
    HAS_ACCESS_TIER = False

try:
    from attune.redis_memory import (
        AgentCredentials,
        ConflictContext,
        RedisShortTermMemory,
        StagedPattern,
        TTLStrategy,
    )

    HAS_REDIS_MEMORY = True
except ImportError:
    HAS_REDIS_MEMORY = False

try:
    from attune.meta_workflows.models import (
        AgentExecutionResult,
        AgentSpec,
        FormResponse,
        FormSchema,
        MetaWorkflowResult,
        MetaWorkflowTemplate,
        TierStrategy,
    )
    from attune.meta_workflows.workflow import (
        MetaWorkflow,
        list_execution_results,
        load_execution_result,
    )

    HAS_META_WORKFLOW = True
except ImportError:
    HAS_META_WORKFLOW = False


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def tmp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory for experiments."""
    storage = tmp_path / "experiments.json"
    return storage


@pytest.fixture
def sample_variant_control() -> dict[str, Any]:
    """Sample control variant data dict."""
    return {
        "variant_id": "exp1_control",
        "name": "Control",
        "description": "Control group",
        "config": {"agents": ["analyzer"]},
        "is_control": True,
        "traffic_percentage": 50.0,
        "impressions": 100,
        "conversions": 30,
        "total_success_score": 25.0,
    }


@pytest.fixture
def sample_variant_treatment() -> dict[str, Any]:
    """Sample treatment variant data dict."""
    return {
        "variant_id": "exp1_treatment_0",
        "name": "Treatment 1",
        "description": "Treatment group",
        "config": {"agents": ["analyzer", "reviewer"]},
        "is_control": False,
        "traffic_percentage": 50.0,
        "impressions": 100,
        "conversions": 45,
        "total_success_score": 40.0,
    }


# ============================================================================
# REDIS MEMORY MODULE
# ============================================================================


@pytest.mark.skipif(
    not HAS_REDIS_MEMORY or not HAS_ACCESS_TIER,
    reason="redis_memory or AccessTier not available",
)
class TestRedisShortTermMemoryMock:
    """Tests for RedisShortTermMemory using the built-in mock mode."""

    @pytest.fixture
    def memory(self) -> RedisShortTermMemory:
        """Create a mock-mode RedisShortTermMemory instance."""
        return RedisShortTermMemory(use_mock=True)

    @pytest.fixture
    def contributor_creds(self) -> AgentCredentials:
        """Create contributor-level credentials."""
        return AgentCredentials(agent_id="agent_contrib", tier=AccessTier.CONTRIBUTOR)

    @pytest.fixture
    def observer_creds(self) -> AgentCredentials:
        """Create observer-level credentials."""
        return AgentCredentials(agent_id="agent_obs", tier=AccessTier.OBSERVER)

    @pytest.fixture
    def validator_creds(self) -> AgentCredentials:
        """Create validator-level credentials."""
        return AgentCredentials(agent_id="agent_val", tier=AccessTier.VALIDATOR)

    @pytest.fixture
    def steward_creds(self) -> AgentCredentials:
        """Create steward-level credentials."""
        return AgentCredentials(agent_id="agent_stew", tier=AccessTier.STEWARD)

    # --- Agent Credentials ---

    def test_agent_credentials_can_read(self, observer_creds: AgentCredentials) -> None:
        """Test all tiers can read."""
        assert observer_creds.can_read() is True

    def test_agent_credentials_observer_cannot_stage(
        self,
        observer_creds: AgentCredentials,
    ) -> None:
        """Test observer cannot stage."""
        assert observer_creds.can_stage() is False

    def test_agent_credentials_contributor_can_stage(
        self,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test contributor can stage."""
        assert contributor_creds.can_stage() is True

    def test_agent_credentials_contributor_cannot_validate(
        self,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test contributor cannot validate."""
        assert contributor_creds.can_validate() is False

    def test_agent_credentials_validator_can_validate(
        self,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test validator can validate."""
        assert validator_creds.can_validate() is True

    def test_agent_credentials_steward_can_administer(
        self,
        steward_creds: AgentCredentials,
    ) -> None:
        """Test steward can administer."""
        assert steward_creds.can_administer() is True

    def test_agent_credentials_validator_cannot_administer(
        self,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test validator cannot administer."""
        assert validator_creds.can_administer() is False

    # --- Working Memory ---

    def test_stash_and_retrieve(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test stashing and retrieving data."""
        memory.stash("my_key", {"findings": 3}, contributor_creds)
        result = memory.retrieve("my_key", contributor_creds)
        assert result == {"findings": 3}

    def test_stash_permission_denied(
        self,
        memory: RedisShortTermMemory,
        observer_creds: AgentCredentials,
    ) -> None:
        """Test stashing as observer raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot write to memory"):
            memory.stash("key", "value", observer_creds)

    def test_retrieve_nonexistent_key(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test retrieving nonexistent key returns None."""
        result = memory.retrieve("nonexistent", contributor_creds)
        assert result is None

    def test_retrieve_other_agent_data(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test retrieving data from another agent by specifying agent_id."""
        memory.stash("shared_key", "shared_data", contributor_creds)

        other_creds = AgentCredentials(agent_id="other_agent", tier=AccessTier.CONTRIBUTOR)
        result = memory.retrieve("shared_key", other_creds, agent_id="agent_contrib")
        assert result == "shared_data"

    def test_clear_working_memory(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test clearing all working memory for an agent."""
        memory.stash("k1", "v1", contributor_creds)
        memory.stash("k2", "v2", contributor_creds)
        count = memory.clear_working_memory(contributor_creds)
        assert count == 2
        assert memory.retrieve("k1", contributor_creds) is None

    # --- Pattern Staging ---

    def test_stage_pattern(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test staging a pattern."""
        pattern = StagedPattern(
            pattern_id="p1",
            agent_id="agent_contrib",
            pattern_type="optimization",
            name="Test Pattern",
            description="A test pattern",
        )
        result = memory.stage_pattern(pattern, contributor_creds)
        assert result is True

    def test_stage_pattern_permission_denied(
        self,
        memory: RedisShortTermMemory,
        observer_creds: AgentCredentials,
    ) -> None:
        """Test staging pattern as observer raises PermissionError."""
        pattern = StagedPattern(
            pattern_id="p1",
            agent_id="agent_obs",
            pattern_type="test",
            name="Test",
            description="d",
        )
        with pytest.raises(PermissionError, match="cannot stage patterns"):
            memory.stage_pattern(pattern, observer_creds)

    def test_get_staged_pattern(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test retrieving a staged pattern."""
        pattern = StagedPattern(
            pattern_id="p2",
            agent_id="agent_contrib",
            pattern_type="debug",
            name="Debug Pattern",
            description="Debug help",
            code="print('debug')",
        )
        memory.stage_pattern(pattern, contributor_creds)
        retrieved = memory.get_staged_pattern("p2", contributor_creds)
        assert retrieved is not None
        assert retrieved.name == "Debug Pattern"
        assert retrieved.code == "print('debug')"

    def test_get_staged_pattern_not_found(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test retrieving non-existent staged pattern returns None."""
        result = memory.get_staged_pattern("nonexistent", contributor_creds)
        assert result is None

    def test_list_staged_patterns(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test listing all staged patterns."""
        for i in range(3):
            pattern = StagedPattern(
                pattern_id=f"list_p{i}",
                agent_id="agent_contrib",
                pattern_type="test",
                name=f"Pattern {i}",
                description="d",
            )
            memory.stage_pattern(pattern, contributor_creds)

        patterns = memory.list_staged_patterns(contributor_creds)
        assert len(patterns) == 3

    def test_promote_pattern(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test promoting a staged pattern."""
        pattern = StagedPattern(
            pattern_id="promote_p",
            agent_id="agent_contrib",
            pattern_type="test",
            name="Promotable",
            description="d",
        )
        memory.stage_pattern(pattern, contributor_creds)
        promoted = memory.promote_pattern("promote_p", validator_creds)
        assert promoted is not None
        assert promoted.name == "Promotable"
        # Should be removed from staging
        assert memory.get_staged_pattern("promote_p", contributor_creds) is None

    def test_promote_pattern_permission_denied(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test promoting pattern as contributor raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot promote patterns"):
            memory.promote_pattern("p1", contributor_creds)

    def test_promote_pattern_not_found(
        self,
        memory: RedisShortTermMemory,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test promoting nonexistent pattern returns None."""
        result = memory.promote_pattern("nonexistent", validator_creds)
        assert result is None

    def test_reject_pattern(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test rejecting a staged pattern."""
        pattern = StagedPattern(
            pattern_id="reject_p",
            agent_id="agent_contrib",
            pattern_type="test",
            name="Rejectable",
            description="d",
        )
        memory.stage_pattern(pattern, contributor_creds)
        result = memory.reject_pattern("reject_p", validator_creds, reason="Not useful")
        assert result is True
        assert memory.get_staged_pattern("reject_p", contributor_creds) is None

    def test_reject_pattern_permission_denied(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test rejecting pattern as contributor raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot reject patterns"):
            memory.reject_pattern("p1", contributor_creds)

    # --- Conflict Negotiation ---

    def test_create_conflict_context(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test creating a conflict context."""
        context = memory.create_conflict_context(
            conflict_id="c1",
            positions={"agent1": "use microservices", "agent2": "use monolith"},
            interests={"agent1": ["scalability"], "agent2": ["simplicity"]},
            credentials=contributor_creds,
            batna="Use modular monolith",
        )
        assert context.conflict_id == "c1"
        assert context.resolved is False

    def test_create_conflict_context_permission_denied(
        self,
        memory: RedisShortTermMemory,
        observer_creds: AgentCredentials,
    ) -> None:
        """Test creating conflict context as observer raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot create conflict context"):
            memory.create_conflict_context(
                conflict_id="c2",
                positions={},
                interests={},
                credentials=observer_creds,
            )

    def test_get_conflict_context(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test retrieving a conflict context."""
        memory.create_conflict_context(
            conflict_id="c3",
            positions={"a": "pos_a"},
            interests={"a": ["interest_a"]},
            credentials=contributor_creds,
        )
        ctx = memory.get_conflict_context("c3", contributor_creds)
        assert ctx is not None
        assert ctx.conflict_id == "c3"

    def test_get_conflict_context_not_found(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test getting nonexistent conflict returns None."""
        result = memory.get_conflict_context("nonexistent", contributor_creds)
        assert result is None

    def test_resolve_conflict(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test resolving a conflict."""
        memory.create_conflict_context(
            conflict_id="c4",
            positions={"a": "pos"},
            interests={"a": ["i"]},
            credentials=contributor_creds,
        )
        result = memory.resolve_conflict("c4", "Adopted compromise", validator_creds)
        assert result is True

        ctx = memory.get_conflict_context("c4", contributor_creds)
        assert ctx is not None
        assert ctx.resolved is True
        assert ctx.resolution == "Adopted compromise"

    def test_resolve_conflict_permission_denied(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test resolving conflict as contributor raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot resolve conflicts"):
            memory.resolve_conflict("c1", "resolution", contributor_creds)

    def test_resolve_conflict_not_found(
        self,
        memory: RedisShortTermMemory,
        validator_creds: AgentCredentials,
    ) -> None:
        """Test resolving nonexistent conflict returns False."""
        result = memory.resolve_conflict("nonexistent", "res", validator_creds)
        assert result is False

    # --- Coordination Signals ---

    def test_send_signal(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test sending a coordination signal."""
        result = memory.send_signal(
            signal_type="ready",
            data={"status": "initialized"},
            credentials=contributor_creds,
            target_agent="agent_receiver",
        )
        assert result is True

    def test_send_signal_broadcast(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test sending a broadcast signal."""
        result = memory.send_signal(
            signal_type="complete",
            data={"task": "done"},
            credentials=contributor_creds,
            target_agent=None,
        )
        assert result is True

    def test_send_signal_permission_denied(
        self,
        memory: RedisShortTermMemory,
        observer_creds: AgentCredentials,
    ) -> None:
        """Test sending signal as observer raises PermissionError."""
        with pytest.raises(PermissionError, match="cannot send signals"):
            memory.send_signal("ready", {}, observer_creds)

    def test_receive_signals(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test receiving coordination signals."""
        receiver_creds = AgentCredentials(agent_id="receiver", tier=AccessTier.CONTRIBUTOR)
        memory.send_signal("ready", {"v": 1}, contributor_creds, target_agent="receiver")
        signals = memory.receive_signals(receiver_creds, signal_type="ready")
        assert len(signals) >= 1
        assert signals[0]["signal_type"] == "ready"

    def test_receive_signals_all_types(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test receiving all signal types (no filter)."""
        receiver_creds = AgentCredentials(agent_id="rcv", tier=AccessTier.CONTRIBUTOR)
        memory.send_signal("ready", {}, contributor_creds, target_agent="rcv")
        memory.send_signal("done", {}, contributor_creds, target_agent="rcv")
        signals = memory.receive_signals(receiver_creds)
        assert len(signals) >= 2

    # --- Session Management ---

    def test_create_session(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test creating a collaboration session."""
        result = memory.create_session("sess_1", contributor_creds, metadata={"topic": "review"})
        assert result is True

    def test_join_session(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test joining an existing session."""
        memory.create_session("sess_join", contributor_creds)
        other = AgentCredentials(agent_id="joiner", tier=AccessTier.CONTRIBUTOR)
        result = memory.join_session("sess_join", other)
        assert result is True

        session = memory.get_session("sess_join", contributor_creds)
        assert session is not None
        assert "joiner" in session["participants"]

    def test_join_session_not_found(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test joining non-existent session returns False."""
        assert memory.join_session("nonexistent", contributor_creds) is False

    def test_join_session_already_member(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test joining session agent is already in does not duplicate."""
        memory.create_session("sess_dup", contributor_creds)
        memory.join_session("sess_dup", contributor_creds)
        session = memory.get_session("sess_dup", contributor_creds)
        assert session is not None
        assert session["participants"].count(contributor_creds.agent_id) == 1

    def test_get_session_not_found(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test getting nonexistent session returns None."""
        assert memory.get_session("nonexistent", contributor_creds) is None

    # --- Health & Stats ---

    def test_ping_mock(self, memory: RedisShortTermMemory) -> None:
        """Test ping returns True in mock mode."""
        assert memory.ping() is True

    def test_get_stats_mock(
        self,
        memory: RedisShortTermMemory,
        contributor_creds: AgentCredentials,
    ) -> None:
        """Test get_stats in mock mode returns correct structure."""
        memory.stash("k1", "v1", contributor_creds)
        stats = memory.get_stats()
        assert stats["mode"] == "mock"
        assert stats["total_keys"] >= 1
        assert "working_keys" in stats
        assert "staged_keys" in stats
        assert "conflict_keys" in stats

    # --- Data classes ---

    def test_staged_pattern_to_dict_and_from_dict(self) -> None:
        """Test StagedPattern roundtrip serialization."""
        pattern = StagedPattern(
            pattern_id="sp1",
            agent_id="a1",
            pattern_type="opt",
            name="Speed up",
            description="desc",
            code="x = 1",
            context={"file": "main.py"},
            confidence=0.8,
            interests=["performance"],
        )
        d = pattern.to_dict()
        restored = StagedPattern.from_dict(d)
        assert restored.pattern_id == "sp1"
        assert restored.code == "x = 1"
        assert restored.confidence == 0.8
        assert restored.interests == ["performance"]

    def test_conflict_context_to_dict_and_from_dict(self) -> None:
        """Test ConflictContext roundtrip serialization."""
        ctx = ConflictContext(
            conflict_id="cc1",
            positions={"a": "pos_a", "b": "pos_b"},
            interests={"a": ["i1"], "b": ["i2"]},
            batna="fallback",
            resolved=True,
            resolution="compromise",
        )
        d = ctx.to_dict()
        restored = ConflictContext.from_dict(d)
        assert restored.conflict_id == "cc1"
        assert restored.resolved is True
        assert restored.resolution == "compromise"
        assert restored.batna == "fallback"

    # --- Mock internal operations ---

    def test_mock_delete_nonexistent(self, memory: RedisShortTermMemory) -> None:
        """Test deleting nonexistent key in mock returns False."""
        result = memory._delete("nonexistent_key")
        assert result is False

    def test_mock_get_expired_key(self, memory: RedisShortTermMemory) -> None:
        """Test expired key returns None in mock mode."""
        # Set with a very short TTL (already expired)
        import time as time_mod

        memory._mock_storage["expired_key"] = (
            "value",
            time_mod.time() - 100,  # Already expired
        )
        result = memory._get("expired_key")
        assert result is None
        assert "expired_key" not in memory._mock_storage

    def test_mock_set_without_ttl(self, memory: RedisShortTermMemory) -> None:
        """Test setting a value without TTL in mock mode."""
        result = memory._set("no_ttl_key", "data", ttl=None)
        assert result is True
        assert memory._get("no_ttl_key") == "data"


@pytest.mark.skipif(
    not HAS_REDIS_MEMORY or not HAS_ACCESS_TIER,
    reason="redis_memory or AccessTier not available",
)
class TestRedisShortTermMemoryRealClient:
    """Tests for RedisShortTermMemory with mocked Redis client (non-mock mode)."""

    def test_get_with_real_client(self) -> None:
        """Test _get delegates to Redis client."""
        with patch("attune.redis_memory.REDIS_AVAILABLE", True):
            mock_redis = MagicMock()
            mock_redis.get.return_value = "stored_value"
            mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
            mem.use_mock = False
            mem._client = mock_redis

            result = mem._get("some_key")
            assert result == "stored_value"
            mock_redis.get.assert_called_once_with("some_key")

    def test_get_returns_none_when_no_result(self) -> None:
        """Test _get returns None when Redis returns falsy."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.get.return_value = None

        assert mem._get("missing") is None

    def test_get_with_no_client(self) -> None:
        """Test _get returns None when client is None."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        assert mem._get("key") is None

    def test_set_with_ttl(self) -> None:
        """Test _set with TTL calls setex."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()

        result = mem._set("key", "val", ttl=60)
        assert result is True
        mem._client.setex.assert_called_once_with("key", 60, "val")

    def test_set_without_ttl(self) -> None:
        """Test _set without TTL calls set."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.set.return_value = True

        result = mem._set("key", "val", ttl=None)
        assert result is True
        mem._client.set.assert_called_once_with("key", "val")

    def test_set_with_no_client(self) -> None:
        """Test _set returns False when client is None."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        assert mem._set("key", "val") is False

    def test_delete_with_real_client(self) -> None:
        """Test _delete delegates to Redis client."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.delete.return_value = 1

        assert mem._delete("key") is True

    def test_delete_with_no_client(self) -> None:
        """Test _delete returns False when client is None."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        assert mem._delete("key") is False

    def test_keys_with_real_client(self) -> None:
        """Test _keys delegates to scan_iter."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.scan_iter.return_value = [b"key1", b"key2"]

        result = mem._keys("pattern*")
        assert result == ["key1", "key2"]

    def test_keys_with_no_client(self) -> None:
        """Test _keys returns empty list when client is None."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        assert mem._keys("*") == []

    def test_ping_real_client_success(self) -> None:
        """Test ping returns True when Redis client is alive."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.ping.return_value = True

        assert mem.ping() is True

    def test_ping_real_client_failure(self) -> None:
        """Test ping returns False when Redis ping raises."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.ping.side_effect = ConnectionError("refused")

        assert mem.ping() is False

    def test_ping_no_client(self) -> None:
        """Test ping returns False when no client."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        assert mem.ping() is False

    def test_get_stats_real_client(self) -> None:
        """Test get_stats with real Redis client."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = MagicMock()
        mem._client.info.return_value = {
            "used_memory_human": "1.5M",
            "used_memory_peak_human": "2.0M",
        }
        mem._client.dbsize.return_value = 42
        mem._client.scan_iter.return_value = []

        stats = mem.get_stats()
        assert stats["mode"] == "redis"
        assert stats["used_memory"] == "1.5M"
        assert stats["total_keys"] == 42

    def test_get_stats_no_client(self) -> None:
        """Test get_stats with no client returns disconnected."""
        mem = RedisShortTermMemory.__new__(RedisShortTermMemory)
        mem.use_mock = False
        mem._client = None

        stats = mem.get_stats()
        assert stats["mode"] == "disconnected"


# ============================================================================
# META-WORKFLOW MODULE
# ============================================================================


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestMetaWorkflow:
    """Tests for MetaWorkflow orchestration."""

    def _make_template(self) -> MetaWorkflowTemplate:
        """Create a minimal template for testing."""
        return MetaWorkflowTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            form_schema=FormSchema(
                title="Test Form",
                description="Test form schema",
                questions=[],
            ),
            agent_composition_rules=[],
            version="1.0.0",
        )

    def test_init_with_template(self, tmp_path: Path) -> None:
        """Test initialization with a template object."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))
        assert wf.template.template_id == "test-template"

    def test_init_requires_template_or_id(self) -> None:
        """Test initialization raises ValueError without template or ID."""
        with pytest.raises(ValueError, match="Must provide either"):
            MetaWorkflow()

    @patch("attune.meta_workflows.workflow.TemplateRegistry")
    def test_init_with_template_id(
        self,
        mock_registry_cls: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test initialization with template_id loads from registry."""
        mock_registry = mock_registry_cls.return_value
        template = self._make_template()
        mock_registry.load_template.return_value = template

        wf = MetaWorkflow(template_id="test-template", storage_dir=str(tmp_path / "exec"))
        assert wf.template.template_id == "test-template"

    @patch("attune.meta_workflows.workflow.TemplateRegistry")
    def test_init_with_template_id_not_found(
        self,
        mock_registry_cls: MagicMock,
    ) -> None:
        """Test initialization with unknown template_id raises ValueError."""
        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ValueError, match="Template not found"):
            MetaWorkflow(template_id="nonexistent")

    def test_execute_mock(self, tmp_path: Path) -> None:
        """Test mock execution of a meta-workflow."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_response = FormResponse(
            template_id="test-template",
            responses={"q1": "answer1"},
        )
        mock_agents = [
            AgentSpec(
                role="Analyzer",
                base_template="code-analyzer",
                tier_strategy=TierStrategy.CHEAP_ONLY,
            ),
        ]

        with patch.object(wf.form_engine, "ask_questions", return_value=mock_response):
            with patch.object(wf.agent_creator, "create_agents", return_value=mock_agents):
                result = wf.execute(mock_execution=True, use_defaults=True)

        assert result.success is True
        assert len(result.agent_results) == 1
        assert result.total_cost > 0

    def test_execute_with_provided_form_response(self, tmp_path: Path) -> None:
        """Test execution with pre-collected form responses."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        form_response = FormResponse(
            template_id="test-template",
            responses={"q1": "val"},
        )
        mock_agents = [
            AgentSpec(
                role="Reviewer",
                base_template="code-reviewer",
                tier_strategy=TierStrategy.PROGRESSIVE,
            ),
        ]

        with patch.object(wf.agent_creator, "create_agents", return_value=mock_agents):
            result = wf.execute(form_response=form_response, mock_execution=True)

        assert result.success is True

    def test_execute_with_pattern_learner(self, tmp_path: Path) -> None:
        """Test execution with pattern learner stores in memory."""
        template = self._make_template()
        mock_learner = MagicMock()
        mock_learner.store_execution_in_memory.return_value = "pattern_123"

        wf = MetaWorkflow(
            template=template,
            storage_dir=str(tmp_path / "exec"),
            pattern_learner=mock_learner,
        )

        form_response = FormResponse(template_id="test-template", responses={})
        with patch.object(wf.agent_creator, "create_agents", return_value=[]):
            result = wf.execute(form_response=form_response, mock_execution=True)

        assert result.success is True
        mock_learner.store_execution_in_memory.assert_called_once()

    def test_execute_error_handling(self, tmp_path: Path) -> None:
        """Test execution error handling creates error result."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        with (
            patch.object(
                wf.form_engine,
                "ask_questions",
                side_effect=RuntimeError("form engine error"),
            ),
            pytest.raises(ValueError, match="Meta-workflow execution failed"),
        ):
            wf.execute(use_defaults=True)

    def test_execute_agents_mock_tier_strategies(self, tmp_path: Path) -> None:
        """Test mock execution handles all tier strategies."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        agents = [
            AgentSpec(role="Cheap", base_template="t", tier_strategy=TierStrategy.CHEAP_ONLY),
            AgentSpec(role="Prog", base_template="t", tier_strategy=TierStrategy.PROGRESSIVE),
            AgentSpec(role="Capable", base_template="t", tier_strategy=TierStrategy.CAPABLE_FIRST),
            AgentSpec(role="Premium", base_template="t", tier_strategy=TierStrategy.PREMIUM_ONLY),
        ]

        results = wf._execute_agents_mock(agents)
        assert len(results) == 4
        assert results[0].tier_used == "cheap"
        assert results[1].tier_used == "capable"
        assert results[2].tier_used == "capable"
        assert results[3].tier_used == "premium"
        assert all(r.success for r in results)

    def test_get_generic_instructions_roles(self, tmp_path: Path) -> None:
        """Test generic instructions generation for various roles."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        analyst_instr = wf._get_generic_instructions("Code Analyst")
        assert "analyst" in analyst_instr.lower()

        reviewer_instr = wf._get_generic_instructions("Code Reviewer")
        assert "reviewer" in reviewer_instr.lower()

        generator_instr = wf._get_generic_instructions("Test Generator")
        assert "generator" in generator_instr.lower() or "content" in generator_instr.lower()

        validator_instr = wf._get_generic_instructions("Schema Validator")
        assert "validator" in validator_instr.lower()

        synthesizer_instr = wf._get_generic_instructions("Result Synthesizer")
        assert "synthesizer" in synthesizer_instr.lower()

        test_instr = wf._get_generic_instructions("Test Runner")
        assert "test" in test_instr.lower()

        # "Doc Specialist" matches "doc" branch (avoids "writer" branch matching first)
        doc_instr = wf._get_generic_instructions("Doc Specialist")
        assert "documentation" in doc_instr.lower()

        # "Content Writer" matches "writer" in the generator branch
        writer_instr = wf._get_generic_instructions("Content Writer")
        assert "content" in writer_instr.lower() or "generator" in writer_instr.lower()

        generic_instr = wf._get_generic_instructions("Custom Agent")
        assert "Custom Agent" in generic_instr

    @patch("attune.meta_workflows.prompt_builder.get_template")
    def test_build_agent_prompt_with_template(
        self,
        mock_get_template: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test prompt building with existing template."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_tmpl = MagicMock()
        mock_tmpl.default_instructions = "You are a test agent."
        mock_get_template.return_value = mock_tmpl

        agent = AgentSpec(
            role="Analyzer",
            base_template="code-analyzer",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            config={"focus": "security"},
            success_criteria=["all issues found"],
            tools=["grep", "ast"],
        )

        prompt = wf._build_agent_prompt(agent)
        assert "Analyzer" in prompt
        assert "You are a test agent." in prompt
        assert "security" in prompt
        assert "all issues found" in prompt
        assert "grep" in prompt

    @patch("attune.meta_workflows.prompt_builder.get_template")
    def test_build_agent_prompt_template_not_found(
        self,
        mock_get_template: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test prompt building falls back to generic when template not found."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        mock_get_template.return_value = None

        agent = AgentSpec(
            role="Reviewer",
            base_template="missing-template",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )

        prompt = wf._build_agent_prompt(agent)
        assert "Reviewer" in prompt

    def test_evaluate_success_criteria_basic(self, tmp_path: Path) -> None:
        """Test success criteria evaluation."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result_success = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=True,
            cost=0.01,
            duration=1.0,
            tier_used="cheap",
            output={"message": "done"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        assert wf._evaluate_success_criteria(result_success, agent) is True

    def test_evaluate_success_criteria_failed_result(self, tmp_path: Path) -> None:
        """Test success criteria evaluation with failed result."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result_fail = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=False,
            cost=0.0,
            duration=0.5,
            tier_used="cheap",
            output={"error": "failed"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
        )
        assert wf._evaluate_success_criteria(result_fail, agent) is False

    def test_evaluate_success_criteria_with_criteria(self, tmp_path: Path) -> None:
        """Test success criteria evaluation with explicit criteria."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = AgentExecutionResult(
            agent_id="a1",
            role="Test",
            success=True,
            cost=0.01,
            duration=1.0,
            tier_used="cheap",
            output={"message": "done"},
        )
        agent = AgentSpec(
            role="Test",
            base_template="t",
            tier_strategy=TierStrategy.CHEAP_ONLY,
            success_criteria=["tests pass", "no regressions"],
        )
        assert wf._evaluate_success_criteria(result, agent) is True

    def test_generate_report(self, tmp_path: Path) -> None:
        """Test report generation."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = MetaWorkflowResult(
            run_id="test-run-001",
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(
                template_id="test-template",
                responses={"q1": "answer"},
            ),
            agents_created=[
                AgentSpec(
                    role="Analyzer",
                    base_template="t",
                    tier_strategy=TierStrategy.CHEAP_ONLY,
                    tools=["grep"],
                    config={"focus": "perf"},
                    success_criteria=["done"],
                ),
            ],
            agent_results=[
                AgentExecutionResult(
                    agent_id="a1",
                    role="Analyzer",
                    success=True,
                    cost=0.05,
                    duration=2.0,
                    tier_used="cheap",
                    output={"message": "ok"},
                ),
            ],
            total_cost=0.05,
            total_duration=2.0,
            success=True,
        )

        report = wf._generate_report(result)
        assert "Meta-Workflow Execution Report" in report
        assert "test-run-001" in report
        assert "$0.05" in report
        assert "Analyzer" in report

    def test_generate_report_with_error(self, tmp_path: Path) -> None:
        """Test report generation for failed execution."""
        template = self._make_template()
        wf = MetaWorkflow(template=template, storage_dir=str(tmp_path / "exec"))

        result = MetaWorkflowResult(
            run_id="error-run",
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(template_id="test-template", responses={}),
            agent_results=[
                AgentExecutionResult(
                    agent_id="a1",
                    role="Broken",
                    success=False,
                    cost=0.0,
                    duration=0.1,
                    tier_used="cheap",
                    output={},
                    error="Something went wrong",
                ),
            ],
            success=False,
            error="Execution failed",
        )

        report = wf._generate_report(result)
        assert "Execution failed" in report
        assert "Something went wrong" in report


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestMetaWorkflowHelpers:
    """Tests for helper functions in meta_workflows.workflow module."""

    def test_load_execution_result(self, tmp_path: Path) -> None:
        """Test loading a saved execution result."""
        run_id = "test-load-run"
        run_dir = tmp_path / run_id
        run_dir.mkdir(parents=True)

        result_data = MetaWorkflowResult(
            run_id=run_id,
            template_id="test-template",
            timestamp=datetime.now().isoformat(),
            form_responses=FormResponse(
                template_id="test-template",
                responses={},
            ),
            success=True,
        )
        (run_dir / "result.json").write_text(result_data.to_json(), encoding="utf-8")

        loaded = load_execution_result(run_id, storage_dir=str(tmp_path))
        assert loaded.run_id == run_id
        assert loaded.success is True

    def test_load_execution_result_not_found(self, tmp_path: Path) -> None:
        """Test loading non-existent result raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Result not found"):
            load_execution_result("nonexistent", storage_dir=str(tmp_path))

    def test_load_execution_result_invalid_json(self, tmp_path: Path) -> None:
        """Test loading invalid JSON result raises ValueError."""
        run_dir = tmp_path / "bad-run"
        run_dir.mkdir()
        (run_dir / "result.json").write_text("not valid json", encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid result file"):
            load_execution_result("bad-run", storage_dir=str(tmp_path))

    def test_list_execution_results(self, tmp_path: Path) -> None:
        """Test listing execution results."""
        # Create some execution directories
        for name in ["run-a", "run-b", "run-c"]:
            d = tmp_path / name
            d.mkdir()
            (d / "result.json").write_text("{}", encoding="utf-8")

        # Create a directory without result.json (should be excluded)
        (tmp_path / "not-a-run").mkdir()

        results = list_execution_results(storage_dir=str(tmp_path))
        assert len(results) == 3
        # Sorted in reverse
        assert results == sorted(results, reverse=True)

    def test_list_execution_results_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test listing from nonexistent directory returns empty list."""
        results = list_execution_results(storage_dir=str(tmp_path / "nonexistent"))
        assert results == []


# ============================================================================
# CLI WORKFLOW COMMANDS MODULE
# ============================================================================


@pytest.mark.skipif(not HAS_META_WORKFLOW, reason="meta_workflows not available")
class TestCLIWorkflowCommands:
    """Tests for CLI workflow commands.

    These tests mock all external dependencies (typer, rich, workflow execution).
    """

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_template_not_found(
        self,
        mock_registry_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with template not found."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ClickExit):
            rw(
                template_id="nonexistent",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=False,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_template_not_found_json_output(
        self,
        mock_registry_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with template not found in JSON mode."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        mock_registry = mock_registry_cls.return_value
        mock_registry.load_template.return_value = None

        with pytest.raises(ClickExit):
            rw(
                template_id="nonexistent",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_success_json(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow success with JSON output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test Template"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-123"
        mock_result.timestamp = "2026-01-01T00:00:00"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.10
        mock_result.total_duration = 5.0
        mock_result.agents_created = []
        mock_result.form_responses.template_id = "test"
        mock_result.form_responses.responses = {}
        mock_result.form_responses.timestamp = "2026-01-01T00:00:00"
        mock_result.form_responses.response_id = "resp-1"
        mock_result.agent_results = []

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Capture print output
        with patch("builtins.print") as mock_print:
            rw(
                template_id="test-template",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

        mock_print.assert_called()
        # The first call should be the JSON output
        call_args = mock_print.call_args_list[0][0][0]
        output = json.loads(call_args)
        assert output["run_id"] == "run-123"
        assert output["success"] is True

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_success_normal_output(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow success with normal console output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test Template"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-456"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.05
        mock_result.total_duration = 2.0
        mock_result.agents_created = [MagicMock()]
        mock_result.agent_results = [
            MagicMock(role="Analyzer", success=True, tier_used="cheap", cost=0.05),
        ]
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        rw(
            template_id="test-template",
            mock=True,
            use_memory=False,
            use_defaults=False,
            user_id="test",
            json_output=False,
        )

        # Verify console.print was called (output displayed)
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_error_result(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow displays error in result."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-err"
        mock_result.success = False
        mock_result.error = "Something broke"
        mock_result.total_cost = 0.0
        mock_result.total_duration = 0.1
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        rw(
            template_id="test-template",
            mock=True,
            use_memory=False,
            use_defaults=True,
            user_id="test",
            json_output=False,
        )

        # Should have printed error info
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_with_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent with matching results."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_match = MagicMock()
        mock_match.template_id = "release-prep"
        mock_match.template_name = "Release Prep"
        mock_match.confidence = 0.85
        mock_match.matched_keywords = ["release", "prepare"]
        mock_match.description = "Prepare for release"

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        di(request="prepare for release", threshold=0.3)

        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_no_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent with no matches."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_detector_cls.return_value.detect.return_value = []

        di(request="something unrelated", threshold=0.3)

        # Should print "no matches" message
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_no_matches(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run with no matching templates."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_detector_cls.return_value.detect.return_value = []

        nlr(request="do something random", auto_run=False, mock=True, use_defaults=True)

        # Should show "couldn't identify" message
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.run_workflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_auto_high_confidence(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
        mock_run_workflow: MagicMock,
    ) -> None:
        """Test natural_language_run auto-runs on high confidence."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match = MagicMock()
        mock_match.template_id = "release-prep"
        mock_match.template_name = "Release Preparation"
        mock_match.confidence = 0.85
        mock_match.description = "Prepare for release"
        mock_match.matched_keywords = ["release"]

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        nlr(request="prepare for release", auto_run=True, mock=True, use_defaults=True)

        mock_run_workflow.assert_called_once()

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_shows_suggestions(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run shows suggestions when not auto-running."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match1 = MagicMock()
        mock_match1.template_id = "release-prep"
        mock_match1.template_name = "Release Prep"
        mock_match1.confidence = 0.7
        mock_match1.description = "Release"
        mock_match1.matched_keywords = ["release"]

        mock_match2 = MagicMock()
        mock_match2.template_id = "test-boost"
        mock_match2.template_name = "Test Boost"
        mock_match2.confidence = 0.4
        mock_match2.description = "Tests"
        mock_match2.matched_keywords = ["test"]

        mock_detector_cls.return_value.detect.return_value = [mock_match1, mock_match2]

        nlr(request="prepare for release", auto_run=False, mock=True, use_defaults=True)

        # Should display suggestions
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_auto_low_confidence(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run does not auto-run on low confidence."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_match = MagicMock()
        mock_match.template_id = "test-boost"
        mock_match.template_name = "Test Boost"
        mock_match.confidence = 0.3  # Below 0.6 threshold
        mock_match.description = "Boost tests"
        mock_match.matched_keywords = ["test"]

        mock_detector_cls.return_value.detect.return_value = [mock_match]

        nlr(request="maybe test something", auto_run=True, mock=True, use_defaults=True)

        # Should show suggestions, NOT auto-run
        assert mock_console.print.call_count > 0

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_detect_intent_error_handling(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test detect_intent handles errors gracefully."""
        from attune.meta_workflows.cli_commands.workflow_commands import detect_intent as di

        mock_detector_cls.return_value.detect.side_effect = RuntimeError("detection failed")

        with pytest.raises(ClickExit):
            di(request="test", threshold=0.3)

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.IntentDetector")
    def test_natural_language_run_error_handling(
        self,
        mock_detector_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test natural_language_run handles errors gracefully."""
        from attune.meta_workflows.cli_commands.workflow_commands import (
            natural_language_run as nlr,
        )

        mock_detector_cls.return_value.detect.side_effect = RuntimeError("detection error")

        with pytest.raises(ClickExit):
            nlr(request="test", auto_run=False, mock=True, use_defaults=True)

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_execution_error_json(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow handles execution error with JSON output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template
        mock_workflow_cls.return_value.execute.side_effect = RuntimeError("execution failed")

        with pytest.raises(ClickExit):
            rw(
                template_id="test",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=True,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_execution_error_normal(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow handles execution error with normal output."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template
        mock_workflow_cls.return_value.execute.side_effect = RuntimeError("execution failed")

        with pytest.raises(ClickExit):
            rw(
                template_id="test",
                mock=True,
                use_memory=False,
                use_defaults=True,
                user_id="test",
                json_output=False,
            )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.PatternLearner")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_memory_enabled(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_pattern_learner_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow with memory integration enabled."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-mem"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.0
        mock_result.total_duration = 1.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Mock the UnifiedMemory import
        with patch(
            "attune.meta_workflows.cli_commands.workflow_commands.UnifiedMemory",
            create=True,
        ):
            # We need to mock the import inside the function
            with patch.dict("sys.modules", {"attune.memory.unified": MagicMock()}):
                rw(
                    template_id="test",
                    mock=True,
                    use_memory=True,
                    use_defaults=True,
                    user_id="test_user",
                    json_output=False,
                )

    @patch("attune.meta_workflows.cli_commands.workflow_commands.console")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.MetaWorkflow")
    @patch("attune.meta_workflows.cli_commands.workflow_commands.TemplateRegistry")
    def test_run_workflow_with_memory_init_failure(
        self,
        mock_registry_cls: MagicMock,
        mock_workflow_cls: MagicMock,
        mock_console: MagicMock,
    ) -> None:
        """Test run_workflow continues when memory initialization fails."""
        from attune.meta_workflows.cli_commands.workflow_commands import run_workflow as rw

        template = MagicMock()
        template.name = "Test"
        mock_registry_cls.return_value.load_template.return_value = template

        mock_result = MagicMock()
        mock_result.run_id = "run-mem-fail"
        mock_result.success = True
        mock_result.error = None
        mock_result.total_cost = 0.0
        mock_result.total_duration = 1.0
        mock_result.agents_created = []
        mock_result.agent_results = []
        mock_result.form_responses = MagicMock()

        mock_workflow_cls.return_value.execute.return_value = mock_result

        # Mock UnifiedMemory to raise on init
        mock_unified = MagicMock()
        mock_unified.side_effect = RuntimeError("Redis not available")

        with patch.dict(
            "sys.modules",
            {"attune.memory.unified": MagicMock(UnifiedMemory=mock_unified)},
        ):
            rw(
                template_id="test",
                mock=True,
                use_memory=True,
                use_defaults=True,
                user_id="test_user",
                json_output=False,
            )

        # Should continue without memory
        mock_workflow_cls.return_value.execute.assert_called_once()


@pytest.mark.skipif(
    not HAS_REDIS_MEMORY or not HAS_ACCESS_TIER,
    reason="redis_memory or AccessTier not available",
)
class TestTTLStrategy:
    """Tests for TTLStrategy enum."""

    def test_ttl_values(self) -> None:
        """Test TTLStrategy values match expected seconds."""
        assert TTLStrategy.WORKING_RESULTS.value == 3600
        assert TTLStrategy.STAGED_PATTERNS.value == 86400
        # COORDINATION removed from TTLStrategy in v5.0
        assert TTLStrategy.CONFLICT_CONTEXT.value == 604800
        assert TTLStrategy.SESSION.value == 1800
