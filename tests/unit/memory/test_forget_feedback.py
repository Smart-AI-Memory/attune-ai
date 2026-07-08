"""The deletion seam emits exactly one memory_feedback event.

A deletion is an explicit "this surfaced finding was noise" verdict —
the noise denominator for the memory analyzer. ``forget_entries`` is
the single emit point; ``forget_by_prefix`` delegates to it and must
not double-count. No deletion (count == 0) emits nothing.

The tests point ATTUNE_HOME at a tmp dir and keep local telemetry
enabled, so the event is observable without touching the real
~/.attune/telemetry/memory_events.jsonl.
"""

from __future__ import annotations

import json

import pytest

from attune.memory import session_stash as ss


class _StubBackend:
    """Minimal SearchableMemoryBackend stand-in for delete/list."""

    def __init__(self, ids):
        self._ids = list(ids)

    def forget(self, ids):
        hit = [i for i in ids if i in self._ids]
        self._ids = [i for i in self._ids if i not in ids]
        return len(hit)

    def recent(self, limit=100, cwd=None):
        return [{"id": i} for i in self._ids]


@pytest.fixture
def events_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_HOME", str(tmp_path))
    monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "1")
    monkeypatch.delenv("DO_NOT_TRACK", raising=False)
    return tmp_path / "telemetry" / "memory_events.jsonl"


def _events(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_forget_entries_emits_one_rejection(events_path):
    backend = _StubBackend(["aaa", "bbb", "ccc"])

    deleted = ss.forget_entries(["aaa", "bbb"], backend=backend, source="reconciler", cwd="/p")

    assert deleted == 2
    evs = _events(events_path)
    assert len(evs) == 1
    assert evs[0]["event"] == "memory_feedback"
    assert evs[0]["verdict"] == "rejected"
    assert evs[0]["source"] == "reconciler"
    assert evs[0]["count"] == 2
    assert evs[0]["cwd"] == "/p"


def test_forget_by_prefix_emits_once_not_twice(events_path):
    backend = _StubBackend(["abc123", "def456"])

    deleted = ss.forget_by_prefix(["abc"], cwd="/p", backend=backend)

    assert deleted == 1
    evs = _events(events_path)
    assert len(evs) == 1  # single emit point — no double count
    assert evs[0]["source"] == "recall_drop"
    assert evs[0]["count"] == 1


def test_no_event_when_nothing_deleted(events_path):
    backend = _StubBackend(["aaa"])

    deleted = ss.forget_entries(["zzz"], backend=backend)

    assert deleted == 0
    assert _events(events_path) == []


def test_telemetry_disabled_still_deletes(events_path, monkeypatch):
    monkeypatch.setenv("ATTUNE_MEMORY_TELEMETRY", "0")
    backend = _StubBackend(["aaa", "bbb"])

    deleted = ss.forget_entries(["aaa"], backend=backend)

    assert deleted == 1  # deletion works even with telemetry off
    assert _events(events_path) == []  # but no event written
