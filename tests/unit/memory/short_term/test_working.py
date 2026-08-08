"""Behavioral tests for WorkingMemory (stash/retrieve/clear/exists/list).

Drives WorkingMemory against an in-memory FakeBase and an optional
FakeSanitizer, covering validation, access control, PII sanitization,
agent-scoped namespacing, and the delete/list paths.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import json

import pytest

from attune.memory.short_term.working import WorkingMemory
from attune.memory.types import AccessTier, AgentCredentials

CONTRIB = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
OBSERVER = AgentCredentials("watcher", AccessTier.OBSERVER)
PREFIX = WorkingMemory.PREFIX_WORKING


class FakeBase:
    def __init__(self, set_returns: bool = True):
        self.store: dict[str, str] = {}
        self.set_returns = set_returns

    def _set(self, key: str, value: str, ttl: object) -> bool:
        if self.set_returns:
            self.store[key] = value
        return self.set_returns

    def _get(self, key: str) -> str | None:
        return self.store.get(key)

    def _keys(self, pattern: str) -> list[str]:
        prefix = pattern.rstrip("*")
        return [k for k in self.store if k.startswith(prefix)]

    def _delete(self, key: str) -> bool:
        return self.store.pop(key, None) is not None

    def _mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    def _delete_many(self, keys: list[str]) -> int:
        return sum(1 for key in keys if self._delete(key))


class FakeSanitizer:
    """Returns a fixed sanitized payload + pii_count, recording calls."""

    def __init__(self, replacement, pii_count: int):
        self.replacement = replacement
        self.pii_count = pii_count
        self.called = False

    def sanitize(self, data):
        self.called = True
        return self.replacement, self.pii_count


class TestStash:
    def test_stores_namespaced_payload(self):
        base = FakeBase()
        WorkingMemory(base).stash("k1", {"v": 1}, CONTRIB)

        full_key = f"{PREFIX}agent_1:k1"
        payload = json.loads(base.store[full_key])
        assert payload["data"] == {"v": 1}
        assert payload["agent_id"] == "agent_1"
        assert "stashed_at" in payload

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            WorkingMemory(FakeBase()).stash("  ", {"v": 1}, CONTRIB)

    def test_observer_cannot_stash(self):
        with pytest.raises(PermissionError, match="cannot write to memory"):
            WorkingMemory(FakeBase()).stash("k1", {"v": 1}, OBSERVER)

    def test_sanitizer_scrubs_pii_and_stores_clean_data(self):
        base = FakeBase()
        sanitizer = FakeSanitizer(replacement={"v": "REDACTED"}, pii_count=2)
        WorkingMemory(base, sanitizer).stash("k1", {"v": "a@b.com"}, CONTRIB)

        assert sanitizer.called is True
        payload = json.loads(base.store[f"{PREFIX}agent_1:k1"])
        assert payload["data"] == {"v": "REDACTED"}

    def test_sanitizer_with_no_pii_still_used(self):
        base = FakeBase()
        sanitizer = FakeSanitizer(replacement={"v": 1}, pii_count=0)
        WorkingMemory(base, sanitizer).stash("k1", {"v": 1}, CONTRIB)

        assert sanitizer.called is True

    def test_skip_sanitization_bypasses_sanitizer(self):
        sanitizer = FakeSanitizer(replacement={"v": "X"}, pii_count=5)
        base = FakeBase()
        WorkingMemory(base, sanitizer).stash("k1", {"v": 1}, CONTRIB, skip_sanitization=True)

        assert sanitizer.called is False
        assert json.loads(base.store[f"{PREFIX}agent_1:k1"])["data"] == {"v": 1}

    def test_returns_storage_result(self):
        assert WorkingMemory(FakeBase(set_returns=False)).stash("k1", 1, CONTRIB) is False


class TestRetrieve:
    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key cannot be empty"):
            WorkingMemory(FakeBase()).retrieve("", CONTRIB)

    def test_missing_returns_none(self):
        assert WorkingMemory(FakeBase()).retrieve("nope", CONTRIB) is None

    def test_returns_stored_data(self):
        base = FakeBase()
        wm = WorkingMemory(base)
        wm.stash("k1", {"v": 42}, CONTRIB)

        assert wm.retrieve("k1", CONTRIB) == {"v": 42}

    def test_agent_id_override_reads_other_owner(self):
        base = FakeBase()
        wm = WorkingMemory(base)
        wm.stash("shared", {"v": 1}, CONTRIB)  # owner agent_1

        # A different caller reads agent_1's key via agent_id override.
        other = AgentCredentials("agent_2", AccessTier.CONTRIBUTOR)
        assert wm.retrieve("shared", other, agent_id="agent_1") == {"v": 1}


class TestClearExistsList:
    def test_clear_deletes_all_agent_keys(self):
        base = FakeBase()
        wm = WorkingMemory(base)
        wm.stash("a", 1, CONTRIB)
        wm.stash("b", 2, CONTRIB)

        deleted = wm.clear(CONTRIB)

        assert deleted == 2
        assert base.store == {}

    def test_clear_returns_zero_when_empty(self):
        assert WorkingMemory(FakeBase()).clear(CONTRIB) == 0

    def test_exists_empty_key_returns_false(self):
        assert WorkingMemory(FakeBase()).exists("", CONTRIB) is False

    def test_exists_true_and_false(self):
        base = FakeBase()
        wm = WorkingMemory(base)
        wm.stash("here", 1, CONTRIB)

        assert wm.exists("here", CONTRIB) is True
        assert wm.exists("absent", CONTRIB) is False

    def test_list_keys_strips_prefix(self):
        base = FakeBase()
        wm = WorkingMemory(base)
        wm.stash("alpha", 1, CONTRIB)
        wm.stash("beta", 2, CONTRIB)

        assert sorted(wm.list_keys(CONTRIB)) == ["alpha", "beta"]
