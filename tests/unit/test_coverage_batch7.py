"""Coverage Batch 7 - Comprehensive tests for maximum statement coverage.

Targets modules with low or no test coverage:
- src/attune/memory/summary_index.py (~283 statements, 9% covered)
- src/attune/workflows/migration.py (~204 statements, 45% covered)
- src/attune/workflows/prompt_mixin.py (~68 statements, 19% covered)
- src/attune/workflows/tier_routing_mixin.py (~32 statements, 40% covered)

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# =============================================================================
# Module 1: memory/summary_index.py
# =============================================================================


class TestAgentContext:
    """Tests for AgentContext dataclass and its methods."""

    def test_agent_context_defaults(self) -> None:
        """Test AgentContext initializes with correct defaults."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(working_on="building auth")
        assert ctx.working_on == "building auth"
        assert ctx.decisions == []
        assert ctx.relevant_files == []
        assert ctx.recent_events == []
        assert ctx.open_questions == []
        assert ctx.topics == []
        assert ctx.session_id == ""
        assert ctx.updated_at == ""

    def test_agent_context_to_prompt_full(self) -> None:
        """Test to_prompt with all fields populated."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(
            working_on="implementing JWT auth",
            decisions=["Use RS256 signing", "Store in httponly cookies"],
            relevant_files=["auth.py", "middleware.py"],
            recent_events=[
                {"type": "decision", "content": "Use RS256"},
                {"type": "started", "content": "JWT module"},
            ],
            open_questions=["Should we support refresh tokens?"],
            topics=["auth", "security"],
            session_id="sess-123",
            updated_at="2026-01-01T00:00:00",
        )

        prompt = ctx.to_prompt()
        assert "## Session Context (from memory)" in prompt
        assert "**Working on:** implementing JWT auth" in prompt
        assert "**Key decisions made:**" in prompt
        assert "- Use RS256 signing" in prompt
        assert "- Store in httponly cookies" in prompt
        assert "**Open questions:**" in prompt
        assert "- Should we support refresh tokens?" in prompt
        assert "**Recent timeline:**" in prompt
        assert "Decision: Use RS256" in prompt
        assert "**Key files:** auth.py, middleware.py" in prompt

    def test_agent_context_to_prompt_empty(self) -> None:
        """Test to_prompt with minimal fields (only working_on empty)."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(working_on="")
        prompt = ctx.to_prompt()
        assert "## Session Context (from memory)" in prompt
        # No "Working on:" section since it's empty
        assert "**Working on:**" not in prompt

    def test_agent_context_to_prompt_truncation(self) -> None:
        """Test to_prompt truncates long lists to expected limits."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(
            working_on="task",
            decisions=[f"decision_{i}" for i in range(10)],
            open_questions=[f"question_{i}" for i in range(8)],
            recent_events=[{"type": "event", "content": f"e{i}"} for i in range(15)],
            relevant_files=[f"file_{i}.py" for i in range(20)],
        )

        prompt = ctx.to_prompt()
        # decisions show last 5
        assert "decision_5" in prompt
        assert "decision_9" in prompt
        # open_questions show last 3
        assert "question_5" in prompt
        assert "question_7" in prompt
        # recent_events show last 5
        assert "e10" in prompt
        assert "e14" in prompt
        # relevant_files show last 10
        assert "file_10.py" in prompt
        assert "file_19.py" in prompt

    def test_agent_context_to_prompt_event_fallback(self) -> None:
        """Test to_prompt falls back to str(event) if no 'content' key."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(
            working_on="task",
            recent_events=[{"type": "custom", "data": "abc"}],
        )
        prompt = ctx.to_prompt()
        # Falls back to str(event) for content
        assert "Custom:" in prompt

    def test_agent_context_to_dict(self) -> None:
        """Test to_dict returns all fields in expected format."""
        from attune.memory.summary_index import AgentContext

        ctx = AgentContext(
            working_on="task",
            decisions=["d1"],
            relevant_files=["f1.py"],
            recent_events=[{"type": "event"}],
            open_questions=["q1"],
            topics=["testing"],
            session_id="sess-1",
            updated_at="2026-01-01",
        )
        d = ctx.to_dict()
        assert d["working_on"] == "task"
        assert d["decisions"] == ["d1"]
        assert d["relevant_files"] == ["f1.py"]
        assert d["recent_events"] == [{"type": "event"}]
        assert d["open_questions"] == ["q1"]
        assert d["topics"] == ["testing"]
        assert d["session_id"] == "sess-1"
        assert d["updated_at"] == "2026-01-01"


class _MockRedisMemory:
    """Lightweight mock for RedisShortTermMemory that uses in-memory dicts."""

    def __init__(self) -> None:
        self.use_mock = True
        self._mock_storage: dict[str, tuple[Any, float | None]] = {}
        self._client = None

    def _delete(self, key: str) -> bool:
        """Delete a key from mock storage."""
        if key in self._mock_storage:
            del self._mock_storage[key]
            return True
        return False


class TestConversationSummaryIndex:
    """Tests for ConversationSummaryIndex with mock Redis backend."""

    @pytest.fixture
    def mock_memory(self) -> _MockRedisMemory:
        """Create a mock Redis memory backend."""
        return _MockRedisMemory()

    @pytest.fixture
    def index(self, mock_memory: _MockRedisMemory) -> Any:
        """Create a ConversationSummaryIndex with mock backend."""
        from attune.memory.summary_index import ConversationSummaryIndex

        return ConversationSummaryIndex(redis_memory=mock_memory, ttl=3600)

    # --- Low-level operations ---

    def test_hset_and_hget_mock(self, index: Any) -> None:
        """Test _hset and _hget with mock storage."""
        result = index._hset("test:key", {"field1": "value1", "field2": "value2"})
        assert result is True

        val = index._hget("test:key", "field1")
        assert val == "value1"

        val2 = index._hget("test:key", "field2")
        assert val2 == "value2"

    def test_hget_missing_key(self, index: Any) -> None:
        """Test _hget returns None for missing key."""
        val = index._hget("nonexistent", "field")
        assert val is None

    def test_hget_missing_field(self, index: Any) -> None:
        """Test _hget returns None for missing field in existing key."""
        index._hset("test:key", {"field1": "value1"})
        val = index._hget("test:key", "missing_field")
        assert val is None

    def test_hgetall_mock(self, index: Any) -> None:
        """Test _hgetall returns full hash."""
        index._hset("test:key", {"a": "1", "b": "2"})
        result = index._hgetall("test:key")
        assert result == {"a": "1", "b": "2"}

    def test_hgetall_missing_key(self, index: Any) -> None:
        """Test _hgetall returns empty dict for missing key."""
        result = index._hgetall("nonexistent")
        assert result == {}

    def test_zadd_and_zrevrange(self, index: Any) -> None:
        """Test _zadd and _zrevrange sorted set operations."""
        index._zadd("zset:key", 1.0, "low")
        index._zadd("zset:key", 3.0, "high")
        index._zadd("zset:key", 2.0, "mid")

        # Should return highest score first
        result = index._zrevrange("zset:key", 0, 2)
        assert result == ["high", "mid", "low"]

    def test_zadd_replaces_existing_member(self, index: Any) -> None:
        """Test _zadd replaces score for existing member."""
        index._zadd("zset:key", 1.0, "item")
        index._zadd("zset:key", 5.0, "item")

        result = index._zrevrange("zset:key", 0, 0)
        assert result == ["item"]

    def test_zrevrange_missing_key(self, index: Any) -> None:
        """Test _zrevrange returns empty list for missing key."""
        result = index._zrevrange("nonexistent", 0, 10)
        assert result == []

    def test_sadd_and_smembers(self, index: Any) -> None:
        """Test _sadd and _smembers set operations."""
        added = index._sadd("set:key", "a", "b", "c")
        assert added == 3

        members = index._smembers("set:key")
        assert members == {"a", "b", "c"}

    def test_sadd_duplicate_members(self, index: Any) -> None:
        """Test _sadd ignores duplicates."""
        index._sadd("set:key", "a", "b")
        added = index._sadd("set:key", "b", "c")
        assert added == 1  # Only "c" is new

        members = index._smembers("set:key")
        assert members == {"a", "b", "c"}

    def test_smembers_missing_key(self, index: Any) -> None:
        """Test _smembers returns empty set for missing key."""
        result = index._smembers("nonexistent")
        assert result == set()

    def test_expire_mock(self, index: Any) -> None:
        """Test _expire sets TTL on existing key."""
        index._hset("test:key", {"a": "1"})
        result = index._expire("test:key", 60)
        assert result is True

    def test_expire_missing_key(self, index: Any) -> None:
        """Test _expire returns False for missing key."""
        result = index._expire("nonexistent", 60)
        assert result is False

    # --- TTL expiration behavior ---

    def test_hget_expired_key(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _hget returns None for expired key."""
        index._hset("test:key", {"a": "1"})
        # Force expiration
        data, _ = mock_memory._mock_storage["test:key"]
        mock_memory._mock_storage["test:key"] = (data, time.time() - 100)

        result = index._hget("test:key", "a")
        assert result is None
        assert "test:key" not in mock_memory._mock_storage

    def test_hgetall_expired_key(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _hgetall returns empty dict for expired key."""
        index._hset("test:key", {"a": "1"})
        data, _ = mock_memory._mock_storage["test:key"]
        mock_memory._mock_storage["test:key"] = (data, time.time() - 100)

        result = index._hgetall("test:key")
        assert result == {}

    def test_zrevrange_expired_key(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _zrevrange returns empty for expired sorted set."""
        index._zadd("zset:key", 1.0, "item")
        data, _ = mock_memory._mock_storage["zset:key"]
        mock_memory._mock_storage["zset:key"] = (data, time.time() - 100)

        result = index._zrevrange("zset:key", 0, 10)
        assert result == []

    def test_smembers_expired_key(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _smembers returns empty set for expired key."""
        index._sadd("set:key", "a")
        data, _ = mock_memory._mock_storage["set:key"]
        mock_memory._mock_storage["set:key"] = (data, time.time() - 100)

        result = index._smembers("set:key")
        assert result == set()

    # --- Non-standard data type handling in mock ---

    def test_hset_overwrites_non_dict_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _hset replaces non-dict stored value with new dict."""
        # Manually put non-dict data
        mock_memory._mock_storage["test:key"] = ("not_a_dict", time.time() + 3600)
        result = index._hset("test:key", {"new": "data"})
        assert result is True

    def test_hgetall_non_dict_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _hgetall returns empty dict for non-dict stored value."""
        mock_memory._mock_storage["test:key"] = ("not_a_dict", None)
        result = index._hgetall("test:key")
        assert result == {}

    def test_hget_non_dict_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _hget returns None when stored data is not a dict."""
        mock_memory._mock_storage["test:key"] = ("not_a_dict", None)
        result = index._hget("test:key", "field")
        assert result is None

    def test_zadd_non_list_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _zadd replaces non-list stored value with list."""
        mock_memory._mock_storage["zset:key"] = ("not_a_list", None)
        result = index._zadd("zset:key", 1.0, "item")
        assert result is True

    def test_zrevrange_non_list_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _zrevrange returns empty list for non-list stored value."""
        mock_memory._mock_storage["zset:key"] = ("not_a_list", None)
        result = index._zrevrange("zset:key", 0, 10)
        assert result == []

    def test_sadd_non_set_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _sadd replaces non-set stored value with set."""
        mock_memory._mock_storage["set:key"] = ("not_a_set", None)
        result = index._sadd("set:key", "item")
        assert result == 1

    def test_smembers_non_set_data(self, index: Any, mock_memory: _MockRedisMemory) -> None:
        """Test _smembers returns empty set for non-set stored value."""
        mock_memory._mock_storage["set:key"] = ("not_a_set", None)
        result = index._smembers("set:key")
        assert result == set()

    # --- Real Redis client path (mock the client) ---

    def test_hset_with_real_client(self) -> None:
        """Test _hset delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hset.return_value = 1

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hset("key", {"f": "v"})
        assert result is True
        mock_mem._client.hset.assert_called_once_with("key", mapping={"f": "v"})

    def test_hset_no_client(self) -> None:
        """Test _hset returns False when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hset("key", {"f": "v"})
        assert result is False

    def test_hget_with_real_client(self) -> None:
        """Test _hget delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hget.return_value = b"value1"

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hget("key", "field")
        assert result == "b'value1'"

    def test_hget_no_client(self) -> None:
        """Test _hget returns None when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hget("key", "field")
        assert result is None

    def test_hget_with_real_client_empty_result(self) -> None:
        """Test _hget returns None when real client returns None."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hget.return_value = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hget("key", "field")
        assert result is None

    def test_hgetall_with_real_client(self) -> None:
        """Test _hgetall delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hgetall.return_value = {b"f1": b"v1"}

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hgetall("key")
        assert isinstance(result, dict)

    def test_hgetall_no_client(self) -> None:
        """Test _hgetall returns {} when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hgetall("key")
        assert result == {}

    def test_hgetall_real_client_empty(self) -> None:
        """Test _hgetall returns {} when real client returns empty."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hgetall.return_value = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._hgetall("key")
        assert result == {}

    def test_zadd_with_real_client(self) -> None:
        """Test _zadd delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.zadd.return_value = 1

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._zadd("key", 1.0, "member")
        assert result is True
        mock_mem._client.zadd.assert_called_once_with("key", {"member": 1.0})

    def test_zadd_no_client(self) -> None:
        """Test _zadd returns False when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._zadd("key", 1.0, "member")
        assert result is False

    def test_zrevrange_with_real_client(self) -> None:
        """Test _zrevrange delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.zrevrange.return_value = [b"item1", b"item2"]

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._zrevrange("key", 0, 5)
        assert result == [b"item1", b"item2"]

    def test_zrevrange_no_client(self) -> None:
        """Test _zrevrange returns [] when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._zrevrange("key", 0, 5)
        assert result == []

    def test_zrevrange_real_client_empty(self) -> None:
        """Test _zrevrange returns [] when real client returns None."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.zrevrange.return_value = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._zrevrange("key", 0, 5)
        assert result == []

    def test_sadd_with_real_client(self) -> None:
        """Test _sadd delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.sadd.return_value = 2

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._sadd("key", "a", "b")
        assert result == 2

    def test_sadd_no_client(self) -> None:
        """Test _sadd returns 0 when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._sadd("key", "a")
        assert result == 0

    def test_smembers_with_real_client(self) -> None:
        """Test _smembers delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.smembers.return_value = {b"a", b"b"}

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._smembers("key")
        assert result == {b"a", b"b"}

    def test_smembers_no_client(self) -> None:
        """Test _smembers returns set() when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._smembers("key")
        assert result == set()

    def test_smembers_real_client_empty(self) -> None:
        """Test _smembers returns set() when real client returns None."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.smembers.return_value = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._smembers("key")
        assert result == set()

    def test_expire_with_real_client(self) -> None:
        """Test _expire delegates to real Redis client."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.expire.return_value = True

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._expire("key", 60)
        assert result is True

    def test_expire_no_client(self) -> None:
        """Test _expire returns False when client is None and not mock."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = None

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        result = idx._expire("key", 60)
        assert result is False

    # --- Public API: update_summary ---

    def test_update_summary_decision_event(self, index: Any) -> None:
        """Test update_summary with a decision event."""
        result = index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT for authentication",
            },
        )
        assert result is True

        # Verify summary stored
        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        decisions = json.loads(summary.get("decisions", "[]"))
        assert "Use JWT for authentication" in decisions

    def test_update_summary_started_event(self, index: Any) -> None:
        """Test update_summary with a started event sets working_on."""
        index.update_summary(
            "sess-1",
            {
                "type": "started",
                "content": "Building login page",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        assert summary["working_on"] == "Building login page"

    def test_update_summary_in_progress_event(self, index: Any) -> None:
        """Test update_summary with in_progress event sets working_on."""
        index.update_summary(
            "sess-1",
            {
                "type": "in_progress",
                "content": "Implementing middleware",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        assert summary["working_on"] == "Implementing middleware"

    def test_update_summary_question_event(self, index: Any) -> None:
        """Test update_summary with a question event."""
        index.update_summary(
            "sess-1",
            {
                "type": "question",
                "content": "Should we use OAuth2?",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        questions = json.loads(summary.get("open_questions", "[]"))
        assert "Should we use OAuth2?" in questions

    def test_update_summary_answered_event(self, index: Any) -> None:
        """Test update_summary answered event removes matching question."""
        # First add a question
        index.update_summary(
            "sess-1",
            {
                "type": "question",
                "content": "Should we use OAuth2?",
            },
        )
        # Then answer it
        index.update_summary(
            "sess-1",
            {
                "type": "answered",
                "content": "oauth2",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        questions = json.loads(summary.get("open_questions", "[]"))
        assert len(questions) == 0

    def test_update_summary_file_modified_event(self, index: Any) -> None:
        """Test update_summary with file_modified event."""
        index.update_summary(
            "sess-1",
            {
                "type": "file_modified",
                "content": "src/auth.py",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        files = json.loads(summary.get("key_files", "[]"))
        assert "src/auth.py" in files

    def test_update_summary_file_modified_no_duplicates(self, index: Any) -> None:
        """Test update_summary does not duplicate file entries."""
        index.update_summary(
            "sess-1",
            {
                "type": "file_modified",
                "content": "src/auth.py",
            },
        )
        index.update_summary(
            "sess-1",
            {
                "type": "file_modified",
                "content": "src/auth.py",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        files = json.loads(summary.get("key_files", "[]"))
        assert files.count("src/auth.py") == 1

    def test_update_summary_topic_extraction(self, index: Any) -> None:
        """Test update_summary extracts and indexes topics."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Implement authentication with JWT tokens",
            },
        )

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        summary = index._hgetall(summary_key)
        topics = json.loads(summary.get("topics", "[]"))
        assert "auth" in topics

        # Topic index should link session
        topic_members = index._smembers(f"{index.PREFIX_TOPIC}auth")
        assert "sess-1" in topic_members

    def test_update_summary_generic_event(self, index: Any) -> None:
        """Test update_summary with unknown event type."""
        result = index.update_summary(
            "sess-1",
            {
                "type": "custom_type",
                "content": "Some generic event",
            },
        )
        assert result is True

    def test_update_summary_missing_type_and_content(self, index: Any) -> None:
        """Test update_summary with empty event dict."""
        result = index.update_summary("sess-1", {})
        assert result is True

    # --- Public API: get_context_for_agent ---

    def test_get_context_for_agent_basic(self, index: Any) -> None:
        """Test get_context_for_agent returns AgentContext."""
        from attune.memory.summary_index import AgentContext

        index.update_summary(
            "sess-1",
            {
                "type": "started",
                "content": "Building auth module",
            },
        )
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT for authentication",
            },
        )

        ctx = index.get_context_for_agent("sess-1")
        assert isinstance(ctx, AgentContext)
        assert ctx.working_on == "Building auth module"
        assert "Use JWT for authentication" in ctx.decisions
        assert ctx.session_id == "sess-1"

    def test_get_context_for_agent_empty_session(self, index: Any) -> None:
        """Test get_context_for_agent for non-existent session."""
        from attune.memory.summary_index import AgentContext

        ctx = index.get_context_for_agent("nonexistent")
        assert isinstance(ctx, AgentContext)
        assert ctx.working_on == ""
        assert ctx.decisions == []

    def test_get_context_for_agent_with_focus_topics(self, index: Any) -> None:
        """Test get_context_for_agent filters by focus_topics."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT for authentication",
            },
        )
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use PostgreSQL database for storage",
            },
        )

        ctx = index.get_context_for_agent("sess-1", focus_topics=["auth"])
        # Only auth-related decisions should remain
        assert any("JWT" in d for d in ctx.decisions)

    def test_get_context_for_agent_invalid_timeline_json(self, index: Any) -> None:
        """Test get_context_for_agent handles invalid JSON in timeline."""
        # Manually inject invalid JSON into the timeline
        timeline_key = f"{index.PREFIX_TIMELINE}sess-1"
        index._zadd(timeline_key, 1.0, "not-valid-json")
        index._zadd(timeline_key, 2.0, json.dumps({"type": "event", "content": "valid"}))

        ctx = index.get_context_for_agent("sess-1")
        # Should skip invalid entry but include valid one
        assert len(ctx.recent_events) == 1

    # --- Public API: recall_decisions ---

    def test_recall_decisions_finds_matching(self, index: Any) -> None:
        """Test recall_decisions returns decisions matching topic."""
        # update_summary extracts topic "auth" from "authentication"
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT authentication tokens",
            },
        )

        # recall_decisions("auth") searches for topic key "auth"
        # and then filters decisions containing "auth" (case-insensitive)
        results = index.recall_decisions("auth")
        assert len(results) >= 1
        assert results[0]["decision"] == "Use JWT authentication tokens"
        assert results[0]["session"] == "sess-1"

    def test_recall_decisions_no_matching(self, index: Any) -> None:
        """Test recall_decisions returns empty when no match."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use PostgreSQL database",
            },
        )

        results = index.recall_decisions("kubernetes")
        assert results == []

    def test_recall_decisions_respects_days_back(self, index: Any) -> None:
        """Test recall_decisions filters by time window."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use database caching for performance",
            },
        )

        # Should find with large window
        results = index.recall_decisions("database", days_back=30)
        assert len(results) >= 1

    def test_recall_decisions_empty_summary(self, index: Any) -> None:
        """Test recall_decisions handles sessions with empty summaries."""
        # Add session to topic index but with no summary
        topic_key = f"{index.PREFIX_TOPIC}testing"
        index._sadd(topic_key, "empty-sess")

        results = index.recall_decisions("testing")
        assert results == []

    def test_recall_decisions_invalid_timestamp(self, index: Any) -> None:
        """Test recall_decisions handles invalid updated_at timestamps."""
        # Add session with invalid timestamp
        summary_key = f"{index.PREFIX_SUMMARY}sess-bad"
        index._hset(
            summary_key,
            {
                "decisions": json.dumps(["testing decision"]),
                "updated_at": "not-a-date",
                "topics": json.dumps(["testing"]),
            },
        )
        topic_key = f"{index.PREFIX_TOPIC}testing"
        index._sadd(topic_key, "sess-bad")

        # Should not crash
        results = index.recall_decisions("testing")
        assert len(results) >= 1

    # --- Public API: get_sessions_by_topic ---

    def test_get_sessions_by_topic(self, index: Any) -> None:
        """Test get_sessions_by_topic returns session IDs."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Improve performance with caching",
            },
        )

        sessions = index.get_sessions_by_topic("performance")
        assert "sess-1" in sessions

    def test_get_sessions_by_topic_no_results(self, index: Any) -> None:
        """Test get_sessions_by_topic returns empty set for unknown topic."""
        sessions = index.get_sessions_by_topic("nonexistent_topic")
        assert sessions == set()

    # --- Public API: clear_session ---

    def test_clear_session(self, index: Any) -> None:
        """Test clear_session removes all session data."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT for authentication",
            },
        )

        result = index.clear_session("sess-1")
        assert result is True

        summary_key = f"{index.PREFIX_SUMMARY}sess-1"
        assert index._hgetall(summary_key) == {}

    def test_clear_session_cleans_topic_indexes(self, index: Any) -> None:
        """Test clear_session removes session from topic indexes."""
        index.update_summary(
            "sess-1",
            {
                "type": "decision",
                "content": "Use JWT for authentication",
            },
        )

        # Verify session is in topic index before clearing
        auth_sessions = index._smembers(f"{index.PREFIX_TOPIC}auth")
        assert "sess-1" in auth_sessions

        index.clear_session("sess-1")

        # Session should be removed from topic index
        auth_sessions_after = index._smembers(f"{index.PREFIX_TOPIC}auth")
        assert "sess-1" not in auth_sessions_after

    def test_clear_session_with_real_client(self) -> None:
        """Test clear_session with real Redis client for topic cleanup."""
        from attune.memory.summary_index import ConversationSummaryIndex

        mock_mem = _MockRedisMemory()
        mock_mem.use_mock = False
        mock_mem._client = MagicMock()
        mock_mem._client.hgetall.return_value = {"topics": json.dumps(["auth"])}

        idx = ConversationSummaryIndex(redis_memory=mock_mem)
        idx._memory._delete = MagicMock()

        result = idx.clear_session("sess-1")
        assert result is True
        mock_mem._client.srem.assert_called_once_with(f"{idx.PREFIX_TOPIC}auth", "sess-1")

    # --- Topic extraction ---

    def test_extract_topics_auth(self, index: Any) -> None:
        """Test _extract_topics finds auth-related topics."""
        topics = index._extract_topics("Implement OAuth login flow")
        assert "auth" in topics

    def test_extract_topics_security(self, index: Any) -> None:
        """Test _extract_topics finds security-related topics."""
        topics = index._extract_topics("Fix XSS vulnerability in form")
        assert "security" in topics

    def test_extract_topics_testing(self, index: Any) -> None:
        """Test _extract_topics finds testing-related topics."""
        topics = index._extract_topics("Add pytest coverage for utils")
        assert "testing" in topics

    def test_extract_topics_database(self, index: Any) -> None:
        """Test _extract_topics finds database-related topics."""
        topics = index._extract_topics("Migrate to PostgreSQL")
        assert "database" in topics

    def test_extract_topics_api(self, index: Any) -> None:
        """Test _extract_topics finds API-related topics."""
        topics = index._extract_topics("Build REST API endpoint")
        assert "api" in topics

    def test_extract_topics_performance(self, index: Any) -> None:
        """Test _extract_topics finds performance-related topics."""
        topics = index._extract_topics("Optimize slow query with cache")
        assert "performance" in topics

    def test_extract_topics_deploy(self, index: Any) -> None:
        """Test _extract_topics finds deployment-related topics."""
        topics = index._extract_topics("Deploy with Docker to production")
        assert "deploy" in topics

    def test_extract_topics_error(self, index: Any) -> None:
        """Test _extract_topics finds error-related topics."""
        topics = index._extract_topics("Debug the exception in handler")
        assert "error" in topics

    def test_extract_topics_refactor(self, index: Any) -> None:
        """Test _extract_topics finds refactoring-related topics."""
        topics = index._extract_topics("Refactor the config module")
        assert "refactor" in topics

    def test_extract_topics_documentation(self, index: Any) -> None:
        """Test _extract_topics finds documentation-related topics."""
        topics = index._extract_topics("Update the docstring for API")
        assert "documentation" in topics

    def test_extract_topics_none_found(self, index: Any) -> None:
        """Test _extract_topics returns empty when no topics match."""
        topics = index._extract_topics("Hello world")
        assert topics == []

    def test_extract_topics_multiple(self, index: Any) -> None:
        """Test _extract_topics can find multiple topics."""
        topics = index._extract_topics("Fix the auth bug and add test coverage")
        assert "auth" in topics
        assert "testing" in topics
        assert "error" in topics


# =============================================================================
# Module 2: workflows/migration.py
# =============================================================================


class TestMigrationConfig:
    """Tests for MigrationConfig dataclass."""

    def test_migration_config_defaults(self) -> None:
        """Test MigrationConfig has correct defaults."""
        from attune.workflows.migration import MIGRATION_MODE_PROMPT, MigrationConfig

        config = MigrationConfig()
        assert config.mode == MIGRATION_MODE_PROMPT
        assert config.remembered_choices == {}
        assert config.show_tips is True
        assert config.last_prompted == {}

    def test_migration_config_load_no_file(self, tmp_path: Path) -> None:
        """Test MigrationConfig.load returns defaults when no file exists."""
        from attune.workflows.migration import MigrationConfig

        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            config = MigrationConfig.load()
        assert config.mode == "prompt"
        assert config.remembered_choices == {}

    def test_migration_config_load_existing_file(self, tmp_path: Path) -> None:
        """Test MigrationConfig.load reads from file."""
        from attune.workflows.migration import MigrationConfig

        config_dir = tmp_path / ".attune"
        config_dir.mkdir()
        config_file = config_dir / "migration.json"
        config_file.write_text(
            json.dumps(
                {
                    "mode": "auto",
                    "remembered_choices": {"old-wf": "new"},
                    "show_tips": False,
                    "last_prompted": {"old-wf": "2026-01-01"},
                },
            ),
        )

        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            config = MigrationConfig.load()
        assert config.mode == "auto"
        assert config.remembered_choices == {"old-wf": "new"}
        assert config.show_tips is False

    def test_migration_config_load_invalid_json(self, tmp_path: Path) -> None:
        """Test MigrationConfig.load handles invalid JSON gracefully."""
        from attune.workflows.migration import MigrationConfig

        config_dir = tmp_path / ".attune"
        config_dir.mkdir()
        config_file = config_dir / "migration.json"
        config_file.write_text("not valid json {{{")

        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            config = MigrationConfig.load()
        # Falls back to defaults
        assert config.mode == "prompt"

    def test_migration_config_save(self, tmp_path: Path) -> None:
        """Test MigrationConfig.save writes to file."""
        from attune.workflows.migration import MigrationConfig

        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            config = MigrationConfig(mode="auto", show_tips=False)
            config.save()

        saved = json.loads((tmp_path / ".attune" / "migration.json").read_text())
        assert saved["mode"] == "auto"
        assert saved["show_tips"] is False

    def test_migration_config_save_os_error(self, tmp_path: Path) -> None:
        """Test MigrationConfig.save handles OSError gracefully."""
        from attune.workflows.migration import MigrationConfig

        config = MigrationConfig()
        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            with patch("builtins.open", side_effect=OSError("disk full")):
                # Should not raise
                config.save()

    def test_migration_config_remember_choice(self, tmp_path: Path) -> None:
        """Test remember_choice stores choice and saves."""
        from attune.workflows.migration import MigrationConfig

        with patch("attune.workflows.migration.Path.cwd", return_value=tmp_path):
            config = MigrationConfig()
            config.remember_choice("old-wf", "new")

        assert config.remembered_choices["old-wf"] == "new"
        # Verify it was saved
        saved = json.loads((tmp_path / ".attune" / "migration.json").read_text())
        assert saved["remembered_choices"]["old-wf"] == "new"


class TestIsInteractive:
    """Tests for is_interactive() function."""

    def test_is_interactive_ci_env(self) -> None:
        """Test is_interactive returns False in CI environments."""
        from attune.workflows.migration import is_interactive

        with patch.dict("os.environ", {"CI": "true"}, clear=False):
            assert is_interactive() is False

    def test_is_interactive_github_actions(self) -> None:
        """Test is_interactive returns False in GitHub Actions."""
        from attune.workflows.migration import is_interactive

        with patch.dict("os.environ", {"GITHUB_ACTIONS": "true"}, clear=False):
            assert is_interactive() is False

    def test_is_interactive_attune_no_interactive(self) -> None:
        """Test is_interactive returns False with ATTUNE_NO_INTERACTIVE."""
        from attune.workflows.migration import is_interactive

        with patch.dict("os.environ", {"ATTUNE_NO_INTERACTIVE": "1"}, clear=False):
            assert is_interactive() is False

    def test_is_interactive_tty_check(self) -> None:
        """Test is_interactive checks stdin.isatty()."""
        from attune.workflows.migration import is_interactive

        env_clean = {
            "CI": "",
            "GITHUB_ACTIONS": "",
            "GITLAB_CI": "",
            "JENKINS_URL": "",
            "CIRCLECI": "",
            "TRAVIS": "",
            "ATTUNE_NO_INTERACTIVE": "",
        }
        with patch.dict("os.environ", env_clean, clear=False):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = True
                assert is_interactive() is True

            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = False
                assert is_interactive() is False


class TestShowMigrationDialog:
    """Tests for show_migration_dialog function."""

    def test_dialog_choice_1_use_new(self) -> None:
        """Test dialog choice 1 returns new syntax."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="1"):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "new-wf"
        assert kwargs == {"mode": "premium"}
        assert remember is False

    def test_dialog_choice_2_use_legacy(self) -> None:
        """Test dialog choice 2 returns legacy syntax."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="2"):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "old-wf"
        assert kwargs == {}
        assert remember is False

    def test_dialog_choice_3_always_new(self) -> None:
        """Test dialog choice 3 returns new syntax with remember=True."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="3"):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "new-wf"
        assert remember is True

    def test_dialog_choice_4_always_legacy(self) -> None:
        """Test dialog choice 4 returns legacy with remember=True."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="4"):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "old-wf"
        assert kwargs == {}
        assert remember is True

    def test_dialog_invalid_then_valid(self) -> None:
        """Test dialog reprompts on invalid input."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", side_effect=["x", "1"]):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "new-wf"

    def test_dialog_eof_defaults_to_new(self) -> None:
        """Test dialog defaults to new syntax on EOF."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", side_effect=EOFError):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "new-wf"
        assert remember is False

    def test_dialog_keyboard_interrupt(self) -> None:
        """Test dialog defaults to new syntax on KeyboardInterrupt."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            name, kwargs, remember = show_migration_dialog("old-wf", "new-wf", {"mode": "premium"})
        assert name == "new-wf"

    def test_dialog_shows_bool_flags(self) -> None:
        """Test dialog builds command with boolean flags correctly."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="1"):
            name, kwargs, _ = show_migration_dialog(
                "old-wf",
                "new-wf",
                {"autonomous": True, "_deprecated": True},
            )
        assert kwargs == {"autonomous": True, "_deprecated": True}

    def test_dialog_with_description(self) -> None:
        """Test dialog includes workflow description when available."""
        from attune.workflows.migration import show_migration_dialog

        with patch("builtins.input", return_value="1"):
            # "code-review" is in WORKFLOW_DESCRIPTIONS
            name, kwargs, _ = show_migration_dialog(
                "pro-review",
                "code-review",
                {"mode": "premium"},
            )
        assert name == "code-review"


class TestShowRemovedWorkflowError:
    """Tests for show_removed_workflow_error function."""

    def test_show_removed_workflow_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test show_removed_workflow_error displays error message."""
        from attune.workflows.migration import show_removed_workflow_error

        show_removed_workflow_error("test5", "test5 was a test artifact")
        output = capsys.readouterr().out
        assert "Workflow Removed" in output
        assert "test5" in output

    def test_show_removed_workflow_error_long_message(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test show_removed_workflow_error wraps long messages."""
        from attune.workflows.migration import show_removed_workflow_error

        long_msg = "This is a very long migration message " * 5
        show_removed_workflow_error("old-wf", long_msg)
        output = capsys.readouterr().out
        assert "old-wf" in output


class TestShowDeprecationWarning:
    """Tests for show_deprecation_warning function."""

    def test_show_deprecation_warning_basic(self) -> None:
        """Test show_deprecation_warning logs warning."""
        from attune.workflows.migration import show_deprecation_warning

        with patch("attune.workflows.migration.logger") as mock_logger:
            show_deprecation_warning("old-wf", "new-wf", {"mode": "premium"})
            mock_logger.warning.assert_called_once()
            msg = mock_logger.warning.call_args[0][0]
            assert "old-wf" in msg
            assert "new-wf" in msg

    def test_show_deprecation_warning_bool_flag(self) -> None:
        """Test show_deprecation_warning handles boolean kwargs."""
        from attune.workflows.migration import show_deprecation_warning

        with patch("attune.workflows.migration.logger") as mock_logger:
            show_deprecation_warning("old-wf", "new-wf", {"autonomous": True})
            msg = mock_logger.warning.call_args[0][0]
            assert "--autonomous" in msg


class TestResolveWorkflowMigration:
    """Tests for resolve_workflow_migration function."""

    def test_resolve_non_aliased_workflow(self) -> None:
        """Test resolve returns original name for non-aliased workflows."""
        from attune.workflows.migration import resolve_workflow_migration

        name, kwargs, migrated = resolve_workflow_migration("code-review")
        assert name == "code-review"
        assert kwargs == {}
        assert migrated is False

    def test_resolve_removed_workflow_interactive(self) -> None:
        """Test resolve raises SystemExit for removed workflow (interactive)."""
        from attune.workflows.migration import resolve_workflow_migration

        with patch("attune.workflows.migration.is_interactive", return_value=True):
            with pytest.raises(SystemExit):
                resolve_workflow_migration("test5")

    def test_resolve_removed_workflow_non_interactive(self) -> None:
        """Test resolve raises SystemExit for removed workflow (non-interactive)."""
        from attune.workflows.migration import resolve_workflow_migration

        with patch("attune.workflows.migration.is_interactive", return_value=False):
            with pytest.raises(SystemExit):
                resolve_workflow_migration("test5")

    def test_resolve_remembered_choice_new(self, tmp_path: Path) -> None:
        """Test resolve uses remembered 'new' choice."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(remembered_choices={"pro-review": "new"})
        name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "code-review"
        assert migrated is True

    def test_resolve_remembered_choice_legacy(self, tmp_path: Path) -> None:
        """Test resolve uses remembered 'legacy' choice."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(remembered_choices={"pro-review": "legacy"})
        name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "pro-review"
        assert kwargs == {}
        assert migrated is True

    def test_resolve_non_interactive_auto_migrate(self) -> None:
        """Test resolve auto-migrates in non-interactive mode."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="prompt")
        with patch("attune.workflows.migration.is_interactive", return_value=False):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "code-review"
        assert migrated is True

    def test_resolve_non_interactive_legacy_mode(self) -> None:
        """Test resolve uses legacy in non-interactive mode with legacy config."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="legacy")
        with patch("attune.workflows.migration.is_interactive", return_value=False):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "pro-review"
        assert migrated is False

    def test_resolve_interactive_auto_mode(self) -> None:
        """Test resolve auto-migrates in interactive mode with auto config."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="auto")
        with patch("attune.workflows.migration.is_interactive", return_value=True):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "code-review"
        assert migrated is True

    def test_resolve_interactive_legacy_mode(self) -> None:
        """Test resolve uses legacy in interactive mode with legacy config."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="legacy")
        with patch("attune.workflows.migration.is_interactive", return_value=True):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "pro-review"
        assert migrated is False

    def test_resolve_interactive_legacy_deprecated_shows_warning(self) -> None:
        """Test resolve shows deprecation warning for deprecated workflow in legacy mode."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="legacy")
        with patch("attune.workflows.migration.is_interactive", return_value=True):
            with patch("attune.workflows.migration.show_deprecation_warning") as mock_warn:
                name, kwargs, migrated = resolve_workflow_migration(
                    "release-prep-legacy",
                    config=config,
                )
                mock_warn.assert_called_once()
        assert name == "release-prep-legacy"

    def test_resolve_interactive_prompt_mode_remember_new(self) -> None:
        """Test resolve prompts and remembers 'new' choice."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="prompt")
        with (
            patch("attune.workflows.migration.is_interactive", return_value=True),
            patch(
                "attune.workflows.migration.show_migration_dialog",
                return_value=("code-review", {"mode": "premium"}, True),
            ),
            patch.object(config, "remember_choice") as mock_remember,
        ):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
            mock_remember.assert_called_once_with("pro-review", "new")
        assert name == "code-review"
        assert migrated is True

    def test_resolve_interactive_prompt_mode_remember_legacy(self) -> None:
        """Test resolve prompts and remembers 'legacy' choice."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="prompt")
        with (
            patch("attune.workflows.migration.is_interactive", return_value=True),
            patch(
                "attune.workflows.migration.show_migration_dialog",
                return_value=("pro-review", {}, True),
            ),
            patch.object(config, "remember_choice") as mock_remember,
        ):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
            mock_remember.assert_called_once_with("pro-review", "legacy")
        assert name == "pro-review"
        assert migrated is False

    def test_resolve_interactive_prompt_mode_no_remember(self) -> None:
        """Test resolve prompts without remembering choice."""
        from attune.workflows.migration import MigrationConfig, resolve_workflow_migration

        config = MigrationConfig(mode="prompt")
        with (
            patch("attune.workflows.migration.is_interactive", return_value=True),
            patch(
                "attune.workflows.migration.show_migration_dialog",
                return_value=("code-review", {"mode": "premium"}, False),
            ),
        ):
            name, kwargs, migrated = resolve_workflow_migration("pro-review", config=config)
        assert name == "code-review"
        assert migrated is True

    def test_resolve_loads_config_if_not_provided(self) -> None:
        """Test resolve loads config from file when not provided."""
        from attune.workflows.migration import resolve_workflow_migration

        with patch("attune.workflows.migration.is_interactive", return_value=False):
            with patch("attune.workflows.migration.MigrationConfig.load") as mock_load:
                from attune.workflows.migration import MigrationConfig

                mock_load.return_value = MigrationConfig(mode="auto")
                name, kwargs, migrated = resolve_workflow_migration("pro-review")
                mock_load.assert_called_once()
        assert name == "code-review"


class TestShowMigrationTip:
    """Tests for show_migration_tip function."""

    def test_show_migration_tip_disabled(self) -> None:
        """Test show_migration_tip does nothing when tips disabled."""
        from attune.workflows.migration import MigrationConfig, show_migration_tip

        with patch(
            "attune.workflows.migration.MigrationConfig.load",
            return_value=MigrationConfig(show_tips=False),
        ):
            show_migration_tip("old-wf", "new-wf", {})
            # No output expected

    def test_show_migration_tip_non_interactive(self) -> None:
        """Test show_migration_tip does nothing in non-interactive mode."""
        from attune.workflows.migration import MigrationConfig, show_migration_tip

        with (
            patch(
                "attune.workflows.migration.MigrationConfig.load",
                return_value=MigrationConfig(show_tips=True),
            ),
            patch("attune.workflows.migration.is_interactive", return_value=False),
        ):
            show_migration_tip("old-wf", "new-wf", {})

    def test_show_migration_tip_interactive(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test show_migration_tip prints tip when interactive and enabled."""
        from attune.workflows.migration import MigrationConfig, show_migration_tip

        with (
            patch(
                "attune.workflows.migration.MigrationConfig.load",
                return_value=MigrationConfig(show_tips=True),
            ),
            patch("attune.workflows.migration.is_interactive", return_value=True),
        ):
            show_migration_tip("old-wf", "new-wf", {"mode": "premium"})
        output = capsys.readouterr().out
        assert "Tip" in output
        assert "new-wf" in output

    def test_show_migration_tip_bool_flags(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test show_migration_tip handles boolean flags in command."""
        from attune.workflows.migration import MigrationConfig, show_migration_tip

        with (
            patch(
                "attune.workflows.migration.MigrationConfig.load",
                return_value=MigrationConfig(show_tips=True),
            ),
            patch("attune.workflows.migration.is_interactive", return_value=True),
        ):
            show_migration_tip("old-wf", "new-wf", {"autonomous": True, "_internal": True})
        output = capsys.readouterr().out
        assert "--autonomous" in output


class TestGetCanonicalWorkflowName:
    """Tests for get_canonical_workflow_name."""

    def test_canonical_name_for_alias(self) -> None:
        """Test returns canonical name for aliased workflow."""
        from attune.workflows.migration import get_canonical_workflow_name

        assert get_canonical_workflow_name("pro-review") == "code-review"

    def test_canonical_name_for_removed(self) -> None:
        """Test returns original name for removed workflow (new_name is None)."""
        from attune.workflows.migration import get_canonical_workflow_name

        assert get_canonical_workflow_name("test5") == "test5"

    def test_canonical_name_for_non_alias(self) -> None:
        """Test returns original name for non-aliased workflow."""
        from attune.workflows.migration import get_canonical_workflow_name

        assert get_canonical_workflow_name("code-review") == "code-review"


class TestListMigrations:
    """Tests for list_migrations."""

    def test_list_migrations_returns_all(self) -> None:
        """Test list_migrations returns info for all aliases."""
        from attune.workflows.migration import WORKFLOW_ALIASES, list_migrations

        migrations = list_migrations()
        assert len(migrations) == len(WORKFLOW_ALIASES)

    def test_list_migrations_consolidated_status(self) -> None:
        """Test list_migrations marks consolidated workflows correctly."""
        from attune.workflows.migration import list_migrations

        migrations = list_migrations()
        pro_review = next(m for m in migrations if m["old_name"] == "pro-review")
        assert pro_review["status"] == "consolidated"
        assert pro_review["new_name"] == "code-review"

    def test_list_migrations_deprecated_status(self) -> None:
        """Test list_migrations marks deprecated workflows correctly."""
        from attune.workflows.migration import list_migrations

        migrations = list_migrations()
        legacy = next(m for m in migrations if m["old_name"] == "release-prep-legacy")
        assert legacy["status"] == "deprecated"

    def test_list_migrations_removed_status(self) -> None:
        """Test list_migrations marks removed workflows correctly."""
        from attune.workflows.migration import list_migrations

        migrations = list_migrations()
        removed = next(m for m in migrations if m["old_name"] == "test5")
        assert removed["status"] == "removed"
        assert removed["new_name"] is None

    def test_list_migrations_no_internal_kwargs(self) -> None:
        """Test list_migrations filters out internal kwargs (starting with _)."""
        from attune.workflows.migration import list_migrations

        migrations = list_migrations()
        for m in migrations:
            for key in m["kwargs"]:
                assert not key.startswith("_")


# =============================================================================
# Module 5: workflows/prompt_mixin.py
# =============================================================================


class _StubWorkflowForPromptMixin:
    """Stub workflow class to test PromptMixin methods."""

    def __init__(self) -> None:

        self.name = "test-workflow"
        self.description = "A test workflow"
        self.stages = ["analyze", "generate", "review"]
        self._config = None

    def get_tier_for_stage(self, stage_name: str) -> Any:
        """Return a mock tier."""
        mock_tier = MagicMock()
        mock_tier.value = "cheap"
        return mock_tier

    def get_model_for_tier(self, tier: Any) -> str:
        """Return a mock model name."""
        return "claude-3-haiku"


# Dynamically create a class that inherits from both
def _make_prompt_mixin_test_class() -> type:
    """Create a test class with PromptMixin."""
    from attune.workflows.prompt_mixin import PromptMixin

    class TestWorkflow(PromptMixin, _StubWorkflowForPromptMixin):
        def __init__(self) -> None:
            _StubWorkflowForPromptMixin.__init__(self)

    return TestWorkflow


class TestPromptMixinDescribe:
    """Tests for PromptMixin.describe method."""

    def test_describe_basic(self) -> None:
        """Test describe returns formatted workflow description."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf.describe()
        assert "Workflow: test-workflow" in result
        assert "Description: A test workflow" in result
        assert "Stages:" in result
        assert "analyze: cheap" in result
        assert "generate: cheap" in result
        assert "review: cheap" in result


class TestPromptMixinBuildCachedSystemPrompt:
    """Tests for PromptMixin._build_cached_system_prompt method."""

    def test_basic_prompt(self) -> None:
        """Test basic system prompt generation with role only."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._build_cached_system_prompt(role="code reviewer")
        assert "You are a code reviewer." in result
        assert "# Instructions" in result

    def test_with_guidelines(self) -> None:
        """Test system prompt with guidelines."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._build_cached_system_prompt(
            role="reviewer",
            guidelines=["Follow PEP 8", "Check security"],
        )
        assert "# Guidelines" in result
        assert "1. Follow PEP 8" in result
        assert "2. Check security" in result

    def test_with_documentation(self) -> None:
        """Test system prompt with documentation."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._build_cached_system_prompt(
            role="reviewer",
            documentation="Coding standards:\n- Use type hints",
        )
        assert "# Reference Documentation" in result
        assert "Coding standards:" in result

    def test_with_examples(self) -> None:
        """Test system prompt with examples."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._build_cached_system_prompt(
            role="reviewer",
            examples=[
                {"input": "def foo(): pass", "output": "Missing type hints"},
                {"input": "def bar(x: int): pass", "output": "Looks good"},
            ],
        )
        assert "# Examples" in result
        assert "Example 1:" in result
        assert "Example 2:" in result
        assert "def foo(): pass" in result

    def test_with_all_sections(self) -> None:
        """Test system prompt with all sections populated."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._build_cached_system_prompt(
            role="expert reviewer",
            guidelines=["Rule 1"],
            documentation="Docs here",
            examples=[{"input": "x", "output": "y"}],
        )
        assert "You are a expert reviewer." in result
        assert "# Guidelines" in result
        assert "# Reference Documentation" in result
        assert "# Examples" in result
        assert "# Instructions" in result


class TestPromptMixinXMLConfig:
    """Tests for PromptMixin XML-related methods."""

    def test_get_xml_config_no_config(self) -> None:
        """Test _get_xml_config returns empty dict when _config is None."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = None
        result = wf._get_xml_config()
        assert result == {}

    def test_get_xml_config_with_config(self) -> None:
        """Test _get_xml_config delegates to config."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {"enabled": True}
        result = wf._get_xml_config()
        assert result == {"enabled": True}

    def test_is_xml_enabled_default_true(self) -> None:
        """Test _is_xml_enabled returns True by default (no config)."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        assert wf._is_xml_enabled() is True

    def test_is_xml_enabled_explicitly_disabled(self) -> None:
        """Test _is_xml_enabled returns False when explicitly disabled."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {"enabled": False}
        assert wf._is_xml_enabled() is False

    def test_is_xml_enabled_true(self) -> None:
        """Test _is_xml_enabled returns True when enabled in config."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {"enabled": True}
        assert wf._is_xml_enabled() is True


class TestPromptMixinRenderPlainPrompt:
    """Tests for PromptMixin._render_plain_prompt method."""

    def test_plain_prompt_basic(self) -> None:
        """Test plain prompt with all sections."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._render_plain_prompt(
            role="analyst",
            goal="Find bugs",
            instructions=["Step 1", "Step 2"],
            constraints=["Be thorough", "No false positives"],
            input_type="code",
            input_payload="def foo(): pass",
        )
        assert "You are a analyst." in result
        assert "Goal: Find bugs" in result
        assert "Instructions:" in result
        assert "1. Step 1" in result
        assert "2. Step 2" in result
        assert "Guidelines:" in result
        assert "- Be thorough" in result
        assert "Input (code):" in result
        assert "def foo(): pass" in result

    def test_plain_prompt_no_instructions(self) -> None:
        """Test plain prompt without instructions."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        result = wf._render_plain_prompt(
            role="analyst",
            goal="Find bugs",
            instructions=[],
            constraints=[],
            input_type="code",
            input_payload="",
        )
        assert "You are a analyst." in result
        assert "Instructions:" not in result
        assert "Guidelines:" not in result


class TestPromptMixinRenderXmlPrompt:
    """Tests for PromptMixin._render_xml_prompt method."""

    def test_render_xml_prompt_disabled_falls_back_to_plain(self) -> None:
        """Test _render_xml_prompt falls back to plain when XML explicitly disabled."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {
            "enabled": False,
        }

        result = wf._render_xml_prompt(
            role="analyst",
            goal="Find bugs",
            instructions=["Step 1"],
            constraints=["Be thorough"],
            input_type="code",
            input_payload="def foo(): pass",
        )
        assert "You are a analyst." in result
        assert "Goal: Find bugs" in result

    def test_render_xml_prompt_enabled_with_template(self) -> None:
        """Test _render_xml_prompt uses XML template when enabled."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {
            "enabled": True,
            "template_name": "test-workflow",
            "schema_version": "1.0",
        }

        mock_context_cls = MagicMock()
        mock_template_instance = MagicMock()
        mock_template_instance.render.return_value = "<xml>rendered</xml>"

        # These are imported inside the function body via:
        # from attune.prompts import PromptContext, XmlPromptTemplate, get_template
        with patch("attune.prompts.PromptContext", mock_context_cls):
            with patch("attune.prompts.get_template", return_value=None):
                with patch(
                    "attune.prompts.XmlPromptTemplate",
                    return_value=mock_template_instance,
                ):
                    result = wf._render_xml_prompt(
                        role="analyst",
                        goal="Find bugs",
                        instructions=["Step 1"],
                        constraints=["Be thorough"],
                        input_type="code",
                        input_payload="def foo(): pass",
                    )
        assert result == "<xml>rendered</xml>"

    def test_render_xml_prompt_enabled_with_existing_template(self) -> None:
        """Test _render_xml_prompt uses existing template from registry."""
        cls = _make_prompt_mixin_test_class()
        wf = cls()
        wf._config = MagicMock()
        wf._config.get_xml_config_for_workflow.return_value = {
            "enabled": True,
            "template_name": "test-workflow",
        }

        mock_template = MagicMock()
        mock_template.render.return_value = "<xml>from registry</xml>"

        with patch("attune.prompts.PromptContext"):
            with patch("attune.prompts.get_template", return_value=mock_template):
                with patch("attune.prompts.XmlPromptTemplate"):
                    result = wf._render_xml_prompt(
                        role="analyst",
                        goal="Find bugs",
                        instructions=[],
                        constraints=[],
                        input_type="code",
                        input_payload="code here",
                        extra={"key": "value"},
                    )
        assert result == "<xml>from registry</xml>"
        mock_template.render.assert_called_once()


# =============================================================================
# Module 6: workflows/tier_routing_mixin.py
# =============================================================================


class _StubWorkflowForTierRouting:
    """Stub workflow class to test TierRoutingMixin."""

    def __init__(self) -> None:
        self.name = "test-workflow"
        self.stages = ["analyze", "generate", "review"]
        self._routing_strategy = None
        self._enable_adaptive_routing = False

    def get_tier_for_stage(self, stage_name: str) -> Any:
        """Return a mock tier."""
        mock_tier = MagicMock()
        mock_tier.value = "cheap"
        return mock_tier

    def _assess_complexity(self, input_data: dict[str, Any]) -> str:
        """Return complexity assessment."""
        return "moderate"

    def _check_adaptive_tier_upgrade(self, stage_name: str, tier: Any) -> Any:
        """Return potentially upgraded tier."""
        return tier


def _make_tier_routing_test_class() -> type:
    """Create a test class with TierRoutingMixin."""
    from attune.workflows.tier_routing_mixin import TierRoutingMixin

    class TestWorkflow(TierRoutingMixin, _StubWorkflowForTierRouting):
        def __init__(self) -> None:
            _StubWorkflowForTierRouting.__init__(self)

    return TestWorkflow


class TestTierRoutingMixinGetTierWithRouting:
    """Tests for TierRoutingMixin._get_tier_with_routing method."""

    def test_static_tier_map_no_routing_strategy(self) -> None:
        """Test uses static tier_map when no routing strategy configured."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        tier = wf._get_tier_with_routing("analyze", {"code": "x"})
        assert tier.value == "cheap"

    def test_with_routing_strategy(self) -> None:
        """Test delegates to routing strategy when configured."""
        cls = _make_tier_routing_test_class()
        wf = cls()

        mock_strategy = MagicMock()
        mock_tier = MagicMock()
        mock_tier.value = "premium"
        mock_strategy.route.return_value = mock_tier
        wf._routing_strategy = mock_strategy

        with patch("attune.workflows.routing.RoutingContext"):
            tier = wf._get_tier_with_routing("analyze", {"code": "x"}, budget_remaining=50.0)
        assert tier.value == "premium"
        mock_strategy.route.assert_called_once()

    def test_routing_strategy_latency_sensitivity_first_stage(self) -> None:
        """Test first stage gets high latency sensitivity."""
        cls = _make_tier_routing_test_class()
        wf = cls()

        mock_strategy = MagicMock()
        mock_strategy.route.return_value = MagicMock(value="cheap")
        wf._routing_strategy = mock_strategy

        captured_context = {}

        def capture_context(**kwargs: Any) -> MagicMock:
            captured_context.update(kwargs)
            return MagicMock()

        with patch(
            "attune.workflows.routing.RoutingContext",
            side_effect=capture_context,
        ):
            wf._get_tier_with_routing("analyze", {})
        assert captured_context["latency_sensitivity"] == "high"

    def test_routing_strategy_latency_sensitivity_middle_stage(self) -> None:
        """Test middle stage gets medium latency sensitivity."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        wf.stages = ["a", "b", "c", "d", "e"]

        mock_strategy = MagicMock()
        mock_strategy.route.return_value = MagicMock(value="capable")
        wf._routing_strategy = mock_strategy

        captured_context = {}

        def capture_context(**kwargs: Any) -> MagicMock:
            captured_context.update(kwargs)
            return MagicMock()

        with patch(
            "attune.workflows.routing.RoutingContext",
            side_effect=capture_context,
        ):
            wf._get_tier_with_routing("b", {})
        assert captured_context["latency_sensitivity"] == "medium"

    def test_routing_strategy_latency_sensitivity_last_stage(self) -> None:
        """Test last stage gets low latency sensitivity."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        wf.stages = ["a", "b", "c", "d", "e"]

        mock_strategy = MagicMock()
        mock_strategy.route.return_value = MagicMock(value="capable")
        wf._routing_strategy = mock_strategy

        captured_context = {}

        def capture_context(**kwargs: Any) -> MagicMock:
            captured_context.update(kwargs)
            return MagicMock()

        with patch(
            "attune.workflows.routing.RoutingContext",
            side_effect=capture_context,
        ):
            wf._get_tier_with_routing("e", {})
        assert captured_context["latency_sensitivity"] == "low"

    def test_routing_strategy_unknown_stage(self) -> None:
        """Test unknown stage defaults to index 0 (high latency)."""
        cls = _make_tier_routing_test_class()
        wf = cls()

        mock_strategy = MagicMock()
        mock_strategy.route.return_value = MagicMock(value="cheap")
        wf._routing_strategy = mock_strategy

        captured_context = {}

        def capture_context(**kwargs: Any) -> MagicMock:
            captured_context.update(kwargs)
            return MagicMock()

        with patch(
            "attune.workflows.routing.RoutingContext",
            side_effect=capture_context,
        ):
            wf._get_tier_with_routing("nonexistent", {})
        assert captured_context["latency_sensitivity"] == "high"

    def test_adaptive_routing_enabled(self) -> None:
        """Test adaptive routing checks for tier upgrade."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        wf._enable_adaptive_routing = True

        upgraded_tier = MagicMock()
        upgraded_tier.value = "premium"
        wf._check_adaptive_tier_upgrade = MagicMock(return_value=upgraded_tier)

        tier = wf._get_tier_with_routing("analyze", {"code": "x"})
        assert tier.value == "premium"
        wf._check_adaptive_tier_upgrade.assert_called_once()

    def test_adaptive_routing_disabled(self) -> None:
        """Test adaptive routing not called when disabled."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        wf._enable_adaptive_routing = False
        wf._check_adaptive_tier_upgrade = MagicMock()

        wf._get_tier_with_routing("analyze", {"code": "x"})
        wf._check_adaptive_tier_upgrade.assert_not_called()

    def test_adaptive_routing_with_strategy(self) -> None:
        """Test adaptive routing works with routing strategy."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        wf._enable_adaptive_routing = True

        mock_strategy = MagicMock()
        base_tier = MagicMock(value="capable")
        mock_strategy.route.return_value = base_tier
        wf._routing_strategy = mock_strategy

        upgraded_tier = MagicMock(value="premium")
        wf._check_adaptive_tier_upgrade = MagicMock(return_value=upgraded_tier)

        with patch("attune.workflows.routing.RoutingContext"):
            tier = wf._get_tier_with_routing("analyze", {"code": "x"})
        assert tier.value == "premium"


class TestEstimateInputTokens:
    """Tests for TierRoutingMixin._estimate_input_tokens method."""

    def test_estimate_basic(self) -> None:
        """Test basic token estimation."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        result = wf._estimate_input_tokens({"code": "x" * 400})
        # ~400 chars / 4 = ~100 tokens (plus JSON overhead)
        assert result > 90

    def test_estimate_empty_data(self) -> None:
        """Test estimation with empty data."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        result = wf._estimate_input_tokens({})
        assert result == 0  # "{}" is 2 chars / 4 = 0

    def test_estimate_non_serializable(self) -> None:
        """Test estimation returns default for non-serializable data."""
        cls = _make_tier_routing_test_class()
        wf = cls()

        # Create an object that fails json.dumps even with default=str
        class BadObj:
            def __str__(self) -> str:
                raise RuntimeError("Cannot stringify")

        # json.dumps with default=str should handle most cases,
        # but TypeError/ValueError are caught
        result = wf._estimate_input_tokens({"data": "normal"})
        assert isinstance(result, int)

    def test_estimate_large_data(self) -> None:
        """Test estimation with large input."""
        cls = _make_tier_routing_test_class()
        wf = cls()
        result = wf._estimate_input_tokens({"code": "x" * 40000})
        assert result > 9000  # ~40000 / 4 = 10000
