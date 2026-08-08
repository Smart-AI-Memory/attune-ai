"""Behavioral tests for SessionManager (collaboration sessions).

Drives SessionManager against an in-memory FakeBase implementing the
_set/_get/_keys storage contract, covering create/join/get/leave/list
including the validation, not-found, idempotent-membership, and
storage-failure branches.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.memory.short_term.sessions import SessionManager
from attune.memory.types import AccessTier, AgentCredentials


class FakeBase:
    """In-memory stand-in for BaseOperations (_set/_get/_mget/_keys)."""

    def __init__(self, set_returns: bool = True):
        self.store: dict[str, str] = {}
        self.set_returns = set_returns
        self.set_calls: list[tuple[str, str, object]] = []

    def _set(self, key: str, value: str, ttl: object) -> bool:
        self.set_calls.append((key, value, ttl))
        if self.set_returns:
            self.store[key] = value
        return self.set_returns

    def _get(self, key: str) -> str | None:
        return self.store.get(key)

    def _mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    def _keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]


def _creds(agent_id: str = "agent_1") -> AgentCredentials:
    return AgentCredentials(agent_id, AccessTier.CONTRIBUTOR)


def _key(session_id: str) -> str:
    return f"{SessionManager.PREFIX_SESSION}{session_id}"


class TestCreateSession:
    def test_creates_with_creator_as_sole_participant(self):
        base = FakeBase()
        mgr = SessionManager(base)

        ok = mgr.create_session("s1", _creds("creator"), metadata={"topic": "x"})

        assert ok is True
        payload = json.loads(base.store[_key("s1")])
        assert payload["session_id"] == "s1"
        assert payload["created_by"] == "creator"
        assert payload["participants"] == ["creator"]
        assert payload["metadata"] == {"topic": "x"}
        assert "created_at" in payload

    def test_metadata_defaults_to_empty_dict(self):
        base = FakeBase()
        mgr = SessionManager(base)

        mgr.create_session("s1", _creds())

        assert json.loads(base.store[_key("s1")])["metadata"] == {}

    @pytest.mark.parametrize("bad_id", ["", "   "])
    def test_empty_session_id_raises(self, bad_id):
        mgr = SessionManager(FakeBase())
        with pytest.raises(ValueError, match="session_id cannot be empty"):
            mgr.create_session(bad_id, _creds())

    def test_non_dict_metadata_raises_type_error(self):
        mgr = SessionManager(FakeBase())
        with pytest.raises(TypeError, match="metadata must be dict"):
            mgr.create_session("s1", _creds(), metadata=["not", "a", "dict"])

    def test_returns_false_when_storage_fails(self):
        base = FakeBase(set_returns=False)
        mgr = SessionManager(base)

        assert mgr.create_session("s1", _creds()) is False


class TestJoinSession:
    def test_empty_session_id_raises(self):
        mgr = SessionManager(FakeBase())
        with pytest.raises(ValueError, match="session_id cannot be empty"):
            mgr.join_session("  ", _creds())

    def test_missing_session_returns_false(self):
        mgr = SessionManager(FakeBase())
        assert mgr.join_session("nope", _creds()) is False

    def test_new_participant_is_appended(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("creator"))

        ok = mgr.join_session("s1", _creds("joiner"))

        assert ok is True
        assert json.loads(base.store[_key("s1")])["participants"] == ["creator", "joiner"]

    def test_existing_participant_not_duplicated(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("creator"))

        ok = mgr.join_session("s1", _creds("creator"))

        assert ok is True
        assert json.loads(base.store[_key("s1")])["participants"] == ["creator"]


class TestGetSession:
    def test_missing_returns_none(self):
        assert SessionManager(FakeBase()).get_session("nope", _creds()) is None

    def test_existing_returns_payload(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("creator"), metadata={"k": "v"})

        info = mgr.get_session("s1", _creds("creator"))

        assert info is not None
        assert info["session_id"] == "s1"
        assert info["metadata"] == {"k": "v"}


class TestLeaveSession:
    def test_empty_session_id_raises(self):
        mgr = SessionManager(FakeBase())
        with pytest.raises(ValueError, match="session_id cannot be empty"):
            mgr.leave_session("", _creds())

    def test_missing_session_returns_false(self):
        assert SessionManager(FakeBase()).leave_session("nope", _creds()) is False

    def test_participant_is_removed(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("creator"))
        mgr.join_session("s1", _creds("joiner"))

        ok = mgr.leave_session("s1", _creds("joiner"))

        assert ok is True
        assert json.loads(base.store[_key("s1")])["participants"] == ["creator"]

    def test_non_participant_returns_false(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("creator"))

        # An agent who never joined cannot leave.
        assert mgr.leave_session("s1", _creds("stranger")) is False
        # Membership is unchanged.
        assert json.loads(base.store[_key("s1")])["participants"] == ["creator"]


class TestListSessions:
    def test_empty_when_no_sessions(self):
        assert SessionManager(FakeBase()).list_sessions() == []

    def test_returns_all_and_skips_empty_values(self):
        base = FakeBase()
        mgr = SessionManager(base)
        mgr.create_session("s1", _creds("a"))
        mgr.create_session("s2", _creds("b"))
        # A key with a falsy value must be skipped by the `if raw` guard.
        base.store[_key("s3")] = ""

        sessions = mgr.list_sessions()

        ids = sorted(s["session_id"] for s in sessions)
        assert ids == ["s1", "s2"]
