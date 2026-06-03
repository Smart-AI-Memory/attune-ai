"""Tests for attune.memory.session_stash (claude-cross-session-memory T1.3).

Backend-agnostic write/recall over the SearchableMemoryBackend protocol,
with a fail-closed PII/secrets gate at write and silent no-op degradation
when no backend is available.
"""

from __future__ import annotations

import pytest

import attune.memory.short_term.security as security_mod
from attune.memory.session_stash import (
    DEFAULT_TTL_DAYS,
    MAX_CONTENT_CHARS,
    SessionStashEntry,
    recall_entries,
    resolve_backend,
    stash_entry,
)


class _FakeBackend:
    """Minimal SearchableMemoryBackend stand-in."""

    def __init__(self, results=None):
        self.stashed: list[tuple] = []
        self._results = results if results is not None else []

    def stash(self, key, value, ttl=None, agent_id=None):
        self.stashed.append((key, value, ttl, agent_id))
        return True

    def search(self, query, limit=10, **filters):
        return list(self._results)


# --------------------------------------------------------------------------
# SessionStashEntry
# --------------------------------------------------------------------------


def test_create_generates_id_and_timestamp():
    e = SessionStashEntry.create(session_id="s1", cwd="/proj", type="decision", content="x")
    assert len(e.id) == 36  # uuid4
    assert e.timestamp.startswith("20")
    assert e.ttl_days == DEFAULT_TTL_DAYS
    assert e.tags == []


def test_invalid_type_rejected():
    with pytest.raises(ValueError, match="invalid type"):
        SessionStashEntry.create(session_id="s", cwd="/p", type="bogus", content="x")


def test_empty_content_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        SessionStashEntry.create(session_id="s", cwd="/p", type="note", content="   ")


def test_content_truncated_to_max(caplog):
    long = "a" * (MAX_CONTENT_CHARS + 50)
    e = SessionStashEntry.create(session_id="s", cwd="/p", type="note", content=long)
    assert len(e.content) == MAX_CONTENT_CHARS


def test_to_dict_round_trips():
    e = SessionStashEntry.create(session_id="s", cwd="/p", type="bug", content="boom", tags=["ci"])
    d = e.to_dict()
    assert d["type"] == "bug" and d["tags"] == ["ci"] and d["content"] == "boom"


# --------------------------------------------------------------------------
# resolve_backend
# --------------------------------------------------------------------------


def test_resolve_backend_injected_wins():
    fb = _FakeBackend()
    assert resolve_backend(fb) is fb


def test_resolve_backend_none_when_unavailable(monkeypatch):
    # No searchable backend registered in the test env.
    assert resolve_backend(None) is None


# --------------------------------------------------------------------------
# stash_entry — gate + degradation
# --------------------------------------------------------------------------


def _entry(content="finding"):
    return SessionStashEntry.create(
        session_id="sess", cwd="/proj", type="decision", content=content
    )


def test_stash_noop_without_backend():
    assert stash_entry(_entry(), backend=None) is False


def test_stash_calls_backend_with_ttl_seconds(monkeypatch):
    # Make the gate a pass-through so we isolate the stash path.
    class _PassThroughGate:
        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _PassThroughGate)
    fb = _FakeBackend()
    e = _entry()
    assert stash_entry(e, backend=fb) is True
    assert len(fb.stashed) == 1
    key, value, ttl, agent_id = fb.stashed[0]
    assert key == e.id
    assert ttl == DEFAULT_TTL_DAYS * 86_400
    assert agent_id == "sess"
    assert value["content"] == "finding"


def test_stash_runs_pii_gate_before_write(monkeypatch):
    calls = {"n": 0}

    class _Gate:
        def sanitize(self, data):
            calls["n"] += 1
            return ("<scrubbed>", 1)

    monkeypatch.setattr(security_mod, "DataSanitizer", _Gate)
    fb = _FakeBackend()
    assert stash_entry(_entry("raw secret-ish text"), backend=fb) is True
    assert calls["n"] == 1, "PII/secrets gate must run before write"
    assert fb.stashed[0][1]["content"] == "<scrubbed>"


def test_stash_fail_closed_when_gate_unavailable(monkeypatch):
    # Remove DataSanitizer so the in-function import raises -> refuse write.
    monkeypatch.delattr(security_mod, "DataSanitizer", raising=False)
    fb = _FakeBackend()
    assert stash_entry(_entry(), backend=fb) is False
    assert fb.stashed == [], "must not persist unsanitized content"


def test_stash_swallows_backend_error(monkeypatch):
    monkeypatch.setattr(
        security_mod, "DataSanitizer", lambda: type("S", (), {"sanitize": lambda self, d: (d, 0)})()
    )

    class _Boom(_FakeBackend):
        def stash(self, *a, **k):
            raise RuntimeError("backend down")

    assert stash_entry(_entry(), backend=_Boom()) is False


# --------------------------------------------------------------------------
# recall_entries
# --------------------------------------------------------------------------


def test_recall_noop_without_backend():
    assert recall_entries("q", backend=None) == []


def test_recall_returns_backend_results():
    fb = _FakeBackend(results=[{"text": "hit", "cwd": "/proj"}])
    out = recall_entries("q", top_k=3, backend=fb)
    assert out == [{"text": "hit", "cwd": "/proj"}]


def test_recall_cwd_soft_sort():
    fb = _FakeBackend(results=[{"text": "other", "cwd": "/x"}, {"text": "mine", "cwd": "/proj"}])
    out = recall_entries("q", cwd="/proj", backend=fb)
    assert out[0]["cwd"] == "/proj", "cwd matches should sort first"


def test_recall_swallows_backend_error():
    class _Boom(_FakeBackend):
        def search(self, *a, **k):
            raise RuntimeError("search down")

    assert recall_entries("q", backend=_Boom()) == []


def test_recall_handles_non_list_result():
    class _Weird(_FakeBackend):
        def search(self, *a, **k):
            return None

    assert recall_entries("q", backend=_Weird()) == []
