"""Shared fixtures for attune-redis tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from attune_redis.config import RedisPluginConfig


class FakeWorkingMemoryResponse:
    """Stub for AMS WorkingMemoryResponse."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}
        self.messages = []
        self.memories = []
        self.session_id = "test-session"
        self.namespace = "attune"


class FakeSessionListResponse:
    """Stub for AMS SessionListResponse."""

    def __init__(self, sessions: list | None = None) -> None:
        self.sessions = sessions or []


class FakeHealthCheckResponse:
    """Stub for AMS HealthCheckResponse."""

    def __init__(self, status: str = "ok") -> None:
        self.status = status


class FakeMemoryRecord:
    """Stub for AMS MemoryRecord."""

    def __init__(
        self,
        record_id: str = "mem-1",
        text: str = "test",
        topics: list[str] | None = None,
        entities: list[str] | None = None,
        memory_type: str = "semantic",
        created_at: Any = None,
    ) -> None:
        self.id = record_id
        self.text = text
        self.topics = topics or []
        self.entities = entities or []
        self.memory_type = memory_type
        self.created_at = created_at


class FakeMemoryRecordResults:
    """Stub for AMS MemoryRecordResults."""

    def __init__(self, memories: list[FakeMemoryRecord] | None = None) -> None:
        self.memories = memories or []


@pytest.fixture()
def redis_config() -> RedisPluginConfig:
    """Create a test configuration."""
    return RedisPluginConfig(
        ams_base_url="http://localhost:9999",
        ams_namespace="test",
        redis_url=None,
        default_session_id="test-session",
        default_user_id="test-user",
    )


@pytest.fixture()
def mock_ams_client() -> MagicMock:
    """Create a mocked MemoryAPIClient."""
    client = MagicMock()

    # Working memory data store (simulates AMS)
    _data: dict[str, Any] = {}

    def _get_working_memory(**kwargs: Any) -> FakeWorkingMemoryResponse:
        return FakeWorkingMemoryResponse(data=dict(_data))

    def _set_working_memory_data(
        session_id: str,
        data: dict[str, Any],
        namespace: str | None = None,
        preserve_existing: bool = True,
    ) -> FakeWorkingMemoryResponse:
        if preserve_existing:
            _data.update(data)
        else:
            _data.clear()
            _data.update(data)
        return FakeWorkingMemoryResponse(data=dict(_data))

    def _update_working_memory_data(
        session_id: str,
        data_updates: dict[str, Any],
        namespace: str | None = None,
        merge_strategy: str = "merge",
    ) -> FakeWorkingMemoryResponse:
        if merge_strategy == "replace":
            _data.clear()
            _data.update(data_updates)
        else:
            _data.update(data_updates)
        return FakeWorkingMemoryResponse(data=dict(_data))

    client.get_working_memory.side_effect = _get_working_memory
    client.set_working_memory_data.side_effect = _set_working_memory_data
    client.update_working_memory_data.side_effect = _update_working_memory_data
    client.health_check.return_value = FakeHealthCheckResponse()
    client.list_sessions.return_value = FakeSessionListResponse()
    client.close.return_value = None
    client.search_long_term_memory.return_value = FakeMemoryRecordResults()
    client.promote_working_memories_to_long_term.return_value = MagicMock()

    # Expose _data for test assertions
    client._test_data = _data

    return client
