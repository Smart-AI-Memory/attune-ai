"""Regression guards for #2235 — malformed Redis JSON must not crash.

The three coordination read paths parsed Redis-stored JSON with bare
``json.loads(raw)``: malformed data raised ``JSONDecodeError`` (and
``join_session`` additionally ``KeyError`` on a missing
``participants``) from deep inside the call. They now degrade through
``_parse_stored_dict``: log + skip / safe default, never raise.

The module is deprecated (replacement: ``attune_redis``), but it still
ships in the wheel — external users in the deprecation window get the
guard, and the module's removal rides the next major.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json
import warnings

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from attune.redis_memory_coordination import (
        CoordinationSignalsMixin,
        SessionManagementMixin,
        _parse_stored_dict,
    )
from attune.memory.types import AccessTier, AgentCredentials


class _FakeSignalsStore(CoordinationSignalsMixin):
    PREFIX_COORDINATION = "coord:"

    def __init__(self, data: dict[str, str]):
        self._data = data

    def _get(self, key: str) -> str | None:
        return self._data.get(key)

    def _set(self, key: str, value: str, ttl: int | None = None) -> bool:
        self._data[key] = value
        return True

    def _keys(self, pattern: str) -> list[str]:
        return list(self._data)


class _FakeSessionStore(SessionManagementMixin):
    PREFIX_SESSION = "session:"

    def __init__(self, data: dict[str, str]):
        self._data = data

    def _get(self, key: str) -> str | None:
        return self._data.get(key)

    def _set(self, key: str, value: str, ttl: int | None = None) -> bool:
        self._data[key] = value
        return True


@pytest.fixture
def creds() -> AgentCredentials:
    return AgentCredentials(agent_id="agent-1", tier=AccessTier.CONTRIBUTOR)


class TestParseStoredDict:
    def test_valid_dict_parses(self):
        assert _parse_stored_dict('{"a": 1}', key="k") == {"a": 1}

    def test_malformed_json_returns_none(self):
        assert _parse_stored_dict("{not json", key="k") is None

    def test_non_dict_payload_returns_none(self):
        assert _parse_stored_dict("[1, 2]", key="k") is None


class TestReceiveSignalsGuard:
    def test_malformed_entry_skipped_good_entries_kept(self, creds):
        good = {"signal_type": "sync", "payload": {"x": 1}}
        store = _FakeSignalsStore(
            {
                "coord:sync:a:agent-1": json.dumps(good),
                "coord:sync:b:agent-1": "{corrupt",
                "coord:sync:c:agent-1": '["a", "list"]',
            }
        )
        signals = store.receive_signals(creds)
        assert signals == [good]


class TestJoinSessionGuard:
    def test_malformed_payload_returns_false(self, creds):
        store = _FakeSessionStore({"session:s1": "{corrupt"})
        assert store.join_session("s1", creds) is False

    def test_missing_participants_key_recovers(self, creds):
        store = _FakeSessionStore({"session:s1": json.dumps({"name": "s1"})})
        assert store.join_session("s1", creds) is True
        saved = json.loads(store._data["session:s1"])
        assert saved["participants"] == ["agent-1"]

    def test_valid_payload_still_joins(self, creds):
        store = _FakeSessionStore({"session:s1": json.dumps({"participants": ["other"]})})
        assert store.join_session("s1", creds) is True
        saved = json.loads(store._data["session:s1"])
        assert saved["participants"] == ["other", "agent-1"]


class TestGetSessionGuard:
    def test_malformed_returns_none(self, creds):
        store = _FakeSessionStore({"session:s1": "{corrupt"})
        assert store.get_session("s1", creds) is None

    def test_non_dict_returns_none(self, creds):
        store = _FakeSessionStore({"session:s1": "[1]"})
        assert store.get_session("s1", creds) is None

    def test_valid_returns_dict(self, creds):
        store = _FakeSessionStore({"session:s1": '{"participants": []}'})
        assert store.get_session("s1", creds) == {"participants": []}
