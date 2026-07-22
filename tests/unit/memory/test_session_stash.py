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
    forget_entries,
    recall_entries,
    recent_entries,
    resolve_backend,
    stash_entry,
)


@pytest.fixture(autouse=True)
def _isolate_ambient_backend(monkeypatch):
    """Ensure ``resolve_backend`` finds no ambient plugin backend by default.

    Without this, a dev environment with a memory-backend plugin installed
    (e.g. attune-redis + a running AMS) makes ``resolve_backend(None)``
    return a *real* backend, so the no-backend-available tests fail
    locally even though they pass in CI (which lacks the optional dep).
    The entry-point lookup is patched to empty so the suite is
    deterministic regardless of what's installed; tests that need an
    entry point set their own monkeypatch, which runs after this and wins.
    """
    import importlib.metadata as md

    monkeypatch.setattr(md, "entry_points", lambda *a, **k: [])


class _FakeBackend:
    """Minimal SearchableMemoryBackend stand-in (key/value stash only)."""

    def __init__(self, results=None):
        self.stashed: list[tuple] = []
        self._results = results if results is not None else []

    def stash(self, key, value, ttl=None, agent_id=None):
        self.stashed.append((key, value, ttl, agent_id))
        return True

    def search(self, query, limit=10, **filters):
        return list(self._results)


class _RememberBackend(_FakeBackend):
    """Searchable backend that also implements the remember() write path."""

    def __init__(self, results=None):
        super().__init__(results)
        self.remembered: list[tuple] = []

    def remember(self, content, *, memory_id=None, session_id=None, topics=None):
        self.remembered.append((content, memory_id, session_id, topics))
        return True


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


def test_resolve_backend_from_entry_point(monkeypatch):
    """A registered, searchable entry-point backend is resolved + returned."""
    import importlib.metadata as md

    searchable = _FakeBackend()

    class _EP:
        name = "fake"

        def load(self):
            def _factory():
                return searchable

            return _factory

    monkeypatch.setattr(md, "entry_points", lambda group=None: [_EP()])
    assert resolve_backend(None) is searchable


def test_resolve_backend_swallows_resolution_error(monkeypatch):
    """A failure in entry-point resolution degrades to None, never raises."""
    import importlib.metadata as md

    def _boom(*args, **kwargs):
        raise RuntimeError("entry point system down")

    monkeypatch.setattr(md, "entry_points", _boom)
    assert resolve_backend(None) is None


def test_resolve_backend_skips_non_searchable_entry_point(monkeypatch):
    """An entry-point object lacking search/stash is skipped, not returned."""
    import importlib.metadata as md

    class _NotSearchable:
        pass

    class _EP:
        name = "fake"

        def load(self):
            def _factory():
                return _NotSearchable()

            return _factory

    monkeypatch.setattr(md, "entry_points", lambda group=None: [_EP()])
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
        def __init__(self, **kwargs):
            pass

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
        def __init__(self, **kwargs):
            pass

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


def test_real_gate_redacts_pii_in_stored_representation():
    """CR-2 regression with the REAL sanitizer (no gate mock): PII must be
    redacted in the stored form. The gate was a silent no-op until
    2026-07-22 — DataSanitizer() constructor defaults disabled both
    scrubbers, so an email passed through unredacted."""
    rb = _RememberBackend()
    entry = _entry("reported by john@example.com during triage")
    assert stash_entry(entry, backend=rb) is True
    content = rb.remembered[0][0]
    assert "john@example.com" not in content, "PII must not reach the backend"
    assert "[EMAIL]" in content


def test_real_gate_refuses_secret_bearing_content():
    """The secrets detector fails CLOSED: content with a credential-shaped
    value is refused entirely (False), never persisted."""
    rb = _RememberBackend()
    fake_key = "sk-abc123def456ghi789jkl"  # pragma: allowlist secret
    entry = _entry(f'the leaked api_key = "{fake_key}" broke CI')
    assert stash_entry(entry, backend=rb) is False
    assert rb.remembered == [], "secret-bearing content must never persist"


def test_stash_swallows_backend_error(monkeypatch):
    class _Sanitizer:
        def __init__(self, **kwargs):
            pass

        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _Sanitizer)

    class _Boom(_FakeBackend):
        def stash(self, *a, **k):
            raise RuntimeError("backend down")

    assert stash_entry(_entry(), backend=_Boom()) is False


def test_stash_uses_remember_when_backend_supports_it(monkeypatch):
    """D7: with a searchable write path, stash_entry writes via remember().

    The finding must go to the long-term (recallable) tier, carrying its
    id, session, and type/cwd topics — NOT the key/value stash fallback.
    """

    class _PassThroughGate:
        def __init__(self, **kwargs):
            pass

        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _PassThroughGate)
    rb = _RememberBackend()
    entry = _entry("a finding worth recalling")
    assert stash_entry(entry, backend=rb) is True
    assert len(rb.remembered) == 1
    content, memory_id, session_id, topics = rb.remembered[0]
    assert content == "a finding worth recalling"
    assert memory_id == entry.id
    assert session_id == "sess"
    assert "type:decision" in topics
    assert "cwd:/proj" in topics
    assert rb.stashed == [], "must use remember(), not the key/value stash fallback"


def test_stash_falls_back_to_keyvalue_when_no_remember(monkeypatch):
    """A backend without remember() degrades to the key/value stash."""

    class _PassThroughGate:
        def __init__(self, **kwargs):
            pass

        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _PassThroughGate)
    fb = _FakeBackend()  # no remember attribute
    assert stash_entry(_entry(), backend=fb) is True
    assert len(fb.stashed) == 1, "fallback must use the key/value stash"


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


# --------------------------------------------------------------------------
# recent_entries — query-less recency recall (SessionStart)
# --------------------------------------------------------------------------


class _RecentBackend(_FakeBackend):
    """Backend that implements the query-less recent() path."""

    def __init__(self, results=None):
        super().__init__(results)
        self.recent_calls: list[dict] = []

    def recent(self, limit=5, **filters):
        self.recent_calls.append({"limit": limit, **filters})
        return list(self._results)


def test_recent_noop_without_backend():
    assert recent_entries(backend=None) == []


def test_recent_empty_when_backend_lacks_recent():
    # _FakeBackend has no recent() — degrade quietly via the getattr guard.
    assert recent_entries(backend=_FakeBackend(results=[{"text": "x"}])) == []


def test_recent_returns_backend_results_and_passes_args():
    rb = _RecentBackend(results=[{"text": "newest", "cwd": "/proj"}])
    out = recent_entries(top_k=3, cwd="/proj", backend=rb)
    assert out == [{"text": "newest", "cwd": "/proj"}]
    assert rb.recent_calls == [{"limit": 3, "cwd": "/proj"}]


def test_recent_swallows_backend_error():
    class _Boom(_RecentBackend):
        def recent(self, *a, **k):
            raise RuntimeError("recent down")

    assert recent_entries(backend=_Boom()) == []


def test_recent_handles_non_list_result():
    class _Weird(_RecentBackend):
        def recent(self, *a, **k):
            return None

    assert recent_entries(backend=_Weird()) == []


# --------------------------------------------------------------------------
# resolve_backend preference (D8): connected upgrade > file fallback
# --------------------------------------------------------------------------


class _Upgrade(_FakeBackend):
    """An AMS-like upgrade backend with a connectivity gate."""

    is_fallback = False

    def __init__(self, connected=True, results=None):
        super().__init__(results)
        self._connected = connected

    def is_connected(self):
        return self._connected


class _Fallback(_FakeBackend):
    """A file-like always-available fallback backend."""

    is_fallback = True

    def is_connected(self):
        return True


def _ep(name, factory):
    class _EP:
        pass

    _EP.name = name
    _EP.load = lambda self: factory
    return _EP()


def test_resolve_prefers_connected_upgrade_over_fallback(monkeypatch):
    import importlib.metadata as md

    upgrade = _Upgrade(connected=True)
    fallback = _Fallback()
    # Fallback listed first (mirrors the real ['file', 'redis'] order).
    monkeypatch.setattr(
        md,
        "entry_points",
        lambda group=None: [_ep("file", lambda: fallback), _ep("redis", lambda: upgrade)],
    )
    assert resolve_backend(None) is upgrade


def test_resolve_falls_back_when_upgrade_disconnected(monkeypatch):
    import importlib.metadata as md

    upgrade = _Upgrade(connected=False)
    fallback = _Fallback()
    monkeypatch.setattr(
        md,
        "entry_points",
        lambda group=None: [_ep("file", lambda: fallback), _ep("redis", lambda: upgrade)],
    )
    assert resolve_backend(None) is fallback


def test_resolve_uses_fallback_when_no_upgrade(monkeypatch):
    import importlib.metadata as md

    fallback = _Fallback()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    assert resolve_backend(None) is fallback


# --------------------------------------------------------------------------
# backend_status — health surfacing (recall-loop triage 2026-06-11):
# an unreachable upgrade backend must be NAMED, not silently degraded past.
# --------------------------------------------------------------------------


def test_backend_status_healthy_upgrade_no_warning(monkeypatch):
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    upgrade = _Upgrade(connected=True)
    fallback = _Fallback()
    monkeypatch.setattr(
        md,
        "entry_points",
        lambda group=None: [_ep("file", lambda: fallback), _ep("redis", lambda: upgrade)],
    )
    status = backend_status()
    assert status["backend"] == "_Upgrade"
    assert status["fallback"] is False
    assert status["unreachable_upgrade"] is None


def test_backend_status_names_disconnected_upgrade(monkeypatch):
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    upgrade = _Upgrade(connected=False)
    fallback = _Fallback()
    monkeypatch.setattr(
        md,
        "entry_points",
        lambda group=None: [_ep("file", lambda: fallback), _ep("redis", lambda: upgrade)],
    )
    status = backend_status()
    assert status["backend"] == "_Fallback"
    assert status["fallback"] is True
    assert status["unreachable_upgrade"] == "redis"


def test_backend_status_names_upgrade_whose_constructor_raises(monkeypatch):
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    fallback = _Fallback()

    def _boom():
        raise RuntimeError("agent-memory-client not installed")

    monkeypatch.setattr(
        md,
        "entry_points",
        lambda group=None: [_ep("file", lambda: fallback), _ep("redis", _boom)],
    )
    status = backend_status()
    assert status["fallback"] is True
    assert status["unreachable_upgrade"] == "redis"


def test_backend_status_fallback_only_is_not_degraded(monkeypatch):
    # A plain install with only the file tier is normal, not degraded.
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    fallback = _Fallback()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    status = backend_status()
    assert status["fallback"] is True
    assert status["unreachable_upgrade"] is None


def test_backend_status_no_backends():
    # autouse fixture already patches entry_points to [].
    from attune.memory.session_stash import backend_status

    assert backend_status() == {
        "backend": None,
        "fallback": False,
        "unreachable_upgrade": None,
        "ok": False,
        "transport": "none",
        "reachability": "unknown",
        "reason": "no_backend",
    }


# --------------------------------------------------------------------------
# backend_status — additive caller-scoped fields (R2/D4,
# cross-provider-memory-transport): ok / transport / reachability / reason.
# Existing keys must be preserved; a caller-local write denial must never
# read as a global service outage.
# --------------------------------------------------------------------------

#: The pre-T1 status keys every consumer may already rely on.
_LEGACY_STATUS_KEYS = {"backend", "fallback", "unreachable_upgrade"}


def test_backend_status_upgrade_reports_direct_reachable(monkeypatch):
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    upgrade = _Upgrade(connected=True)
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("redis", lambda: upgrade)])
    status = backend_status()
    assert _LEGACY_STATUS_KEYS <= status.keys()
    assert status["ok"] is True
    assert status["transport"] == "direct"
    assert status["reachability"] == "reachable"
    assert status["reason"] is None


def test_backend_status_writable_fallback_is_ok_file_transport(monkeypatch):
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    class _WritableFallback(_Fallback):
        def probe_write(self):
            return True

    fallback = _WritableFallback()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    status = backend_status()
    assert status["ok"] is True
    assert status["transport"] == "file"
    assert status["reachability"] == "reachable"
    assert status["reason"] is None


def test_backend_status_local_denial_is_not_a_global_outage(monkeypatch):
    """The Codex-sandbox shape: file fallback resolved but unwritable.

    Must report a caller-scoped denial (unreachable_local +
    file_write_denied), never success — and never a service-down claim.
    """
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    class _DeniedFallback(_Fallback):
        def probe_write(self):
            return False

    fallback = _DeniedFallback()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    status = backend_status()
    assert status["backend"] == "_DeniedFallback"
    assert status["fallback"] is True
    assert status["ok"] is False
    assert status["transport"] == "none"
    assert status["reachability"] == "unreachable_local"
    assert status["reason"] == "file_write_denied"
    # No upgrade is registered — local denial must not invent one.
    assert status["unreachable_upgrade"] is None


def test_backend_status_fallback_without_probe_stays_usable(monkeypatch):
    # A backend predating probe_write degrades to "usable, reachability
    # unknown" — never a false denial.
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    fallback = _Fallback()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    status = backend_status()
    assert status["ok"] is True
    assert status["transport"] == "file"
    assert status["reachability"] == "unknown"
    assert status["reason"] is None


def test_backend_status_probe_exception_is_denial_not_crash(monkeypatch):
    # never-raises contract: a probe that blows up reads as a local denial.
    import importlib.metadata as md

    from attune.memory.session_stash import backend_status

    class _ExplodingProbe(_Fallback):
        def probe_write(self):
            raise RuntimeError("probe blew up")

    fallback = _ExplodingProbe()
    monkeypatch.setattr(md, "entry_points", lambda group=None: [_ep("file", lambda: fallback)])
    status = backend_status()
    assert status["ok"] is False
    assert status["reachability"] == "unreachable_local"
    assert status["reason"] == "file_write_denied"


# --------------------------------------------------------------------------
# D8 zero-infra round-trip: stash_entry -> recall_entries via the file backend
# --------------------------------------------------------------------------


def test_file_fallback_roundtrip_no_infra(tmp_path, monkeypatch):
    """The headline D8 guarantee: cross-session recall works with no AMS.

    Uses a real FileStashBackend over tmp_path — no Redis, no Ollama, no
    server — and proves stash_entry -> recall_entries finds the finding.
    """
    from attune.memory.file_stash import FileStashBackend

    class _PassThroughGate:
        def __init__(self, **kwargs):
            pass

        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _PassThroughGate)
    be = FileStashBackend(base_dir=tmp_path / "stash")
    entry = SessionStashEntry.create(
        session_id="s1",
        cwd="/proj",
        type="decision",
        content="the retry loop deadlocks under heavy load",
        tags=["ci"],
    )
    assert stash_entry(entry, backend=be) is True
    hits = recall_entries("retry loop deadlocks", top_k=5, cwd="/proj", backend=be)
    assert hits, "stashed finding must be recallable with zero infra"
    assert any("retry loop" in (h.get("text") or "") for h in hits)
    assert hits[0]["cwd"] == "/proj"


# --------------------------------------------------------------------------
# forget_entries
# --------------------------------------------------------------------------


class _ForgetBackend(_FakeBackend):
    """Searchable backend that also implements precise forget()."""

    def __init__(self, results=None):
        super().__init__(results)
        self.forgotten: list[list[str]] = []

    def forget(self, ids):
        self.forgotten.append(list(ids))
        return len(ids)


def test_forget_entries_delegates_to_backend():
    fb = _ForgetBackend()
    assert forget_entries(["a", "b"], backend=fb) == 2
    assert fb.forgotten == [["a", "b"]]


def test_forget_entries_empty_ids_noop():
    fb = _ForgetBackend()
    assert forget_entries([], backend=fb) == 0
    assert fb.forgotten == []


def test_forget_entries_noop_without_backend():
    assert forget_entries(["a"]) == 0  # ambient resolution isolated -> None


def test_forget_entries_backend_without_forget_degrades():
    assert forget_entries(["a"], backend=_FakeBackend()) == 0


def test_forget_entries_swallows_backend_error():
    class _Boom(_ForgetBackend):
        def forget(self, ids):
            raise RuntimeError("ams down")

    assert forget_entries(["a"], backend=_Boom()) == 0


# --------------------------------------------------------------------------
# forget_by_prefix
# --------------------------------------------------------------------------


class _RecentForgetBackend(_ForgetBackend):
    """Forget-capable backend with a recent() listing to resolve against."""

    def __init__(self, ids):
        super().__init__()
        self._ids = list(ids)

    def recent(self, limit=5, **filters):
        return [{"id": i, "text": "x", "topics": []} for i in self._ids[:limit]]


def test_forget_by_prefix_resolves_unique_prefix():
    from attune.memory.session_stash import forget_by_prefix

    fb = _RecentForgetBackend(["aaaa1111-x", "bbbb2222-y"])
    assert forget_by_prefix(["aaaa1111"], backend=fb) == 1
    assert fb.forgotten == [["aaaa1111-x"]]


def test_forget_by_prefix_skips_ambiguous_and_unknown():
    from attune.memory.session_stash import forget_by_prefix

    fb = _RecentForgetBackend(["abc-1", "abc-2", "def-3"])
    # "abc" matches two records, "zzz" matches none -> both skipped.
    assert forget_by_prefix(["abc", "zzz", "def"], backend=fb) == 1
    assert fb.forgotten == [["def-3"]]


def test_forget_by_prefix_full_id_works():
    from attune.memory.session_stash import forget_by_prefix

    fb = _RecentForgetBackend(["abc-1"])
    assert forget_by_prefix(["abc-1"], backend=fb) == 1


def test_forget_by_prefix_empty_or_blank_noop():
    from attune.memory.session_stash import forget_by_prefix

    fb = _RecentForgetBackend(["abc-1"])
    assert forget_by_prefix([], backend=fb) == 0
    assert forget_by_prefix(["  ", ""], backend=fb) == 0
    assert fb.forgotten == []


def test_forget_by_prefix_backend_without_recent_degrades():
    from attune.memory.session_stash import forget_by_prefix

    assert forget_by_prefix(["abc"], backend=_ForgetBackend()) == 0


def test_forget_by_prefix_noop_without_backend():
    from attune.memory.session_stash import forget_by_prefix

    # Ambient resolution isolated by the autouse fixture -> no backend.
    assert forget_by_prefix(["abc"]) == 0


def test_forget_by_prefix_swallows_recent_error():
    from attune.memory.session_stash import forget_by_prefix

    class _RecentBoom(_ForgetBackend):
        def recent(self, limit=5, **filters):
            raise RuntimeError("listing failed")

    fb = _RecentBoom()
    assert forget_by_prefix(["abc"], backend=fb) == 0
    assert fb.forgotten == []
