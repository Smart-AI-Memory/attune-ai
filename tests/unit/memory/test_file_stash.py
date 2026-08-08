"""Tests for FileStashBackend — the zero-infra searchable default (D8).

Exercises the keyword + recency + cwd recall, TTL pruning, key/value
path, and the SearchableMemoryBackend protocol surface. All isolated to
``tmp_path`` (never touches the real ``~/.attune``).
"""

from __future__ import annotations

import json
import time

import pytest

from attune.memory.file_stash import DEFAULT_TTL_DAYS, FileStashBackend


@pytest.fixture
def backend(tmp_path):
    be = FileStashBackend(base_dir=tmp_path / "stash")
    yield be
    be.close()


# --------------------------------------------------------------------------
# remember / search round-trip
# --------------------------------------------------------------------------


def test_remember_then_search_finds_by_keyword(backend):
    assert backend.remember("the authentication retry loop is flaky", memory_id="m1") is True
    hits = backend.search("authentication flaky")
    assert len(hits) == 1
    assert hits[0]["id"] == "m1"
    assert "authentication" in hits[0]["text"]


def test_search_empty_query_returns_empty(backend):
    backend.remember("anything at all", memory_id="m1")
    assert backend.search("") == []
    assert backend.search("   ") == []


def test_search_excludes_zero_overlap(backend):
    backend.remember("redis connection pooling notes", memory_id="m1")
    assert backend.search("kubernetes ingress") == []


def test_search_respects_limit(backend):
    for i in range(5):
        backend.remember(f"shared keyword finding number {i}", memory_id=f"m{i}")
    hits = backend.search("shared keyword finding", limit=3)
    assert len(hits) == 3


def test_topics_are_searchable(backend):
    backend.remember("opaque body text", memory_id="m1", topics=["type:bug", "cwd:/proj"])
    hits = backend.search("bug")
    assert len(hits) == 1 and hits[0]["id"] == "m1"


# --------------------------------------------------------------------------
# cwd surfacing + boost
# --------------------------------------------------------------------------


def test_cwd_surfaced_from_topics(backend):
    backend.remember("a finding", memory_id="m1", topics=["cwd:/home/proj"])
    hits = backend.search("finding")
    assert hits[0]["cwd"] == "/home/proj"


def test_cwd_match_boosts_ranking(backend):
    backend.remember("matching keyword here", memory_id="other", topics=["cwd:/x"])
    backend.remember("matching keyword here", memory_id="mine", topics=["cwd:/proj"])
    hits = backend.search("matching keyword", cwd="/proj")
    assert hits[0]["id"] == "mine", "same-cwd finding should rank first"


# --------------------------------------------------------------------------
# recency ordering + TTL prune (controlled ts via direct file write)
# --------------------------------------------------------------------------


def _write_records(be: FileStashBackend, records):
    be._findings.parent.mkdir(parents=True, exist_ok=True)
    be._findings.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def test_recency_breaks_ties(backend):
    now = time.time()
    _write_records(
        backend,
        [
            {
                "id": "old",
                "text": "same keyword text",
                "topics": [],
                "cwd": None,
                "ts": now - 5 * 86400,
            },
            {"id": "new", "text": "same keyword text", "topics": [], "cwd": None, "ts": now - 60},
        ],
    )
    hits = backend.search("same keyword text")
    assert [h["id"] for h in hits][0] == "new", "more recent finding ranks first"


def test_ttl_prunes_expired_on_search(backend):
    now = time.time()
    _write_records(
        backend,
        [
            {"id": "fresh", "text": "keyword alpha", "topics": [], "cwd": None, "ts": now - 60},
            {
                "id": "stale",
                "text": "keyword alpha",
                "topics": [],
                "cwd": None,
                "ts": now - (DEFAULT_TTL_DAYS + 1) * 86400,
            },
        ],
    )
    hits = backend.search("keyword alpha")
    ids = [h["id"] for h in hits]
    assert "fresh" in ids and "stale" not in ids


def test_remember_prunes_expired(backend):
    now = time.time()
    _write_records(
        backend,
        # 31 days: unambiguously past the 30-day TTL (avoid the exact-boundary
        # epsilon trap that flakes on coarse-clock platforms — see CLAUDE.md
        # "edge-of-bucket time tests fail on Windows").
        [{"id": "stale", "text": "x y", "topics": [], "cwd": None, "ts": now - 31 * 86400}],
    )
    backend.remember("brand new finding", memory_id="new")
    ids = {r["id"] for r in backend._load_records()}
    assert ids == {"new"}, "expired record dropped on the next write"


# --------------------------------------------------------------------------
# key/value path + protocol surface
# --------------------------------------------------------------------------


def test_kv_round_trip(backend):
    assert backend.stash("k", {"v": 1}) is True
    assert backend.retrieve("k") == {"v": 1}
    assert backend.retrieve("missing") is None


def test_kv_delete_and_keys(backend):
    backend.stash("a", 1)
    backend.stash("b", 2)
    assert sorted(backend.keys()) == ["a", "b"]
    # Extract the mutating call before asserting (no side-effect inside assert).
    deleted = backend.delete("a")
    assert deleted is True
    deleted_again = backend.delete("a")
    assert deleted_again is False
    assert backend.keys() == ["b"]


def test_retrieve_many_matches_per_key_retrieve(backend):
    backend.stash("a", 1)
    backend.stash("b", {"v": 2})
    got = backend.retrieve_many(["a", "b", "missing"])
    assert got == {"a": 1, "b": {"v": 2}, "missing": None}
    assert got == {k: backend.retrieve(k) for k in ["a", "b", "missing"]}


def test_retrieve_many_empty_keys(backend):
    assert backend.retrieve_many([]) == {}


def test_is_fallback_and_protocol_surface(backend):
    assert FileStashBackend.is_fallback is True
    assert backend.is_connected() is True
    assert backend.promote() is True
    assert backend.supports_realtime() is False
    assert backend.supports_distributed() is False
    stats = backend.get_stats()
    assert stats["backend"] == "file"


def test_remember_returns_false_on_unexpected_error(backend, monkeypatch):
    monkeypatch.setattr(
        backend, "_load_records", lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert backend.remember("x y z") is False


def test_search_handles_read_error(backend):
    # A directory at the findings path makes read_text raise -> [] (no crash).
    backend._findings.mkdir(parents=True)
    assert backend.search("anything") == []


def test_kv_stash_returns_false_on_write_error(backend):
    # A directory at the kv path makes the atomic replace fail -> False.
    backend._kv.mkdir(parents=True)
    assert backend.stash("k", {"v": 1}) is False


def test_corrupt_lines_are_skipped(backend):
    backend._findings.parent.mkdir(parents=True, exist_ok=True)
    good = json.dumps(
        {"id": "ok", "text": "valid keyword", "topics": [], "cwd": None, "ts": time.time()}
    )
    backend._findings.write_text(f"not json\n{good}\n", encoding="utf-8")
    hits = backend.search("valid keyword")
    assert len(hits) == 1 and hits[0]["id"] == "ok"


def test_default_base_dir_is_under_home(tmp_path, monkeypatch):
    """No-arg construction (the entry-point path) defaults under ~/.attune."""
    import pathlib

    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    be = FileStashBackend()
    assert str(be._dir).startswith(str(tmp_path))
    remembered = be.remember("default dir finding", memory_id="d1")
    assert remembered is True


def test_construction_survives_mkdir_failure(tmp_path):
    """A base_dir that can't be created is logged, not fatal."""
    blocker = tmp_path / "afile"
    blocker.write_text("not a dir", encoding="utf-8")
    be = FileStashBackend(base_dir=blocker / "stash")  # parent is a file
    assert be is not None  # construction did not raise


def test_blank_lines_in_findings_are_skipped(backend):
    good = json.dumps(
        {"id": "ok", "text": "keyword here", "topics": [], "cwd": None, "ts": time.time()}
    )
    backend._findings.parent.mkdir(parents=True, exist_ok=True)
    backend._findings.write_text(f"\n\n{good}\n\n", encoding="utf-8")
    hits = backend.search("keyword here")
    assert len(hits) == 1


def test_remember_survives_rewrite_failure(backend):
    """A write failure during remember is swallowed (best-effort, non-fatal)."""
    backend._findings.mkdir(parents=True)  # findings path is a dir -> replace fails
    # _load_records returns [] (read fails on a dir), _rewrite hits OSError + logs.
    backend.remember("a finding that cannot persist")  # must not raise


def test_kv_delete_swallows_write_error(backend, monkeypatch):
    """A write error while deleting a present key returns False, no raise."""
    # Key is present (load patched), but the kv path is a directory so the
    # atomic replace fails -> the OSError branch returns False.
    monkeypatch.setattr(backend, "_load_kv", lambda: {"k": 1})
    backend._kv.mkdir(parents=True)
    result = backend.delete("k")
    assert result is False


# --------------------------------------------------------------------------
# explicit prune() — forced age sweep (parity with the AMS backend)
# --------------------------------------------------------------------------


def test_default_ttl_is_30_days():
    """The zero-infra retention default is 30 days (project-revisit window)."""
    assert DEFAULT_TTL_DAYS == 30


def test_prune_drops_expired_keeps_fresh(backend):
    now = time.time()
    _write_records(
        backend,
        [
            {"id": "fresh", "text": "a", "topics": [], "cwd": None, "ts": now - 60},
            {"id": "stale", "text": "b", "topics": [], "cwd": None, "ts": now - 31 * 86400},
        ],
    )
    dropped = backend.prune()
    assert dropped == 1
    assert {r["id"] for r in backend._load_records()} == {"fresh"}


def test_prune_respects_explicit_max_age(backend):
    now = time.time()
    _write_records(
        backend,
        [
            {"id": "keep", "text": "a", "topics": [], "cwd": None, "ts": now - 3 * 86400},
            {"id": "drop", "text": "b", "topics": [], "cwd": None, "ts": now - 10 * 86400},
        ],
    )
    # 5-day window: the 10-day-old record goes, the 3-day-old stays.
    dropped = backend.prune(max_age_days=5)
    assert dropped == 1
    assert {r["id"] for r in backend._load_records()} == {"keep"}


def test_prune_no_findings_file_returns_zero(backend):
    # Nothing stashed yet -> findings.jsonl absent -> clean no-op.
    assert backend.prune() == 0


def test_prune_nothing_expired_returns_zero_and_keeps_all(backend):
    now = time.time()
    _write_records(
        backend,
        [{"id": "a", "text": "x", "topics": [], "cwd": None, "ts": now - 60}],
    )
    assert backend.prune() == 0
    assert {r["id"] for r in backend._load_records()} == {"a"}


def test_prune_swallows_read_error(backend):
    # A directory at the findings path makes read_text raise OSError -> 0, no crash.
    backend._findings.mkdir(parents=True)
    assert backend.prune() == 0


def test_prune_skips_blank_and_corrupt_drops_nondict(backend):
    # Exercises the blank-line skip, the JSONDecodeError skip, and the
    # non-dict branch (a bare number is dropped) — alongside a kept record.
    now = time.time()
    backend._findings.parent.mkdir(parents=True, exist_ok=True)
    valid = json.dumps({"id": "keep", "text": "x", "topics": [], "cwd": None, "ts": now - 60})
    backend._findings.write_text(f"\n{valid}\nnot valid json\n123\n", encoding="utf-8")
    dropped = backend.prune()
    # Only the non-dict record counts as dropped; blank + corrupt lines are
    # silently skipped, the fresh dict is kept.
    assert dropped == 1
    assert {r["id"] for r in backend._load_records()} == {"keep"}


# --------------------------------------------------------------------------
# recent() — query-less recency recall (powers SessionStart)
# --------------------------------------------------------------------------


def test_recent_newest_first(backend):
    now = time.time()
    _write_records(
        backend,
        [
            {"id": "old", "text": "a", "topics": [], "cwd": None, "ts": now - 3600},
            {"id": "new", "text": "b", "topics": [], "cwd": None, "ts": now - 60},
            {"id": "mid", "text": "c", "topics": [], "cwd": None, "ts": now - 600},
        ],
    )
    assert [r["id"] for r in backend.recent()] == ["new", "mid", "old"]


def test_recent_cwd_priority(backend):
    now = time.time()
    _write_records(
        backend,
        [
            # newest overall is /other; /proj is older but should surface first
            {"id": "other", "text": "a", "topics": [], "cwd": "/other", "ts": now - 60},
            {"id": "proj", "text": "b", "topics": [], "cwd": "/proj", "ts": now - 600},
        ],
    )
    ids = [r["id"] for r in backend.recent(cwd="/proj")]
    assert ids[0] == "proj", "same-cwd finding surfaces first despite being older"


def test_recent_respects_limit(backend):
    now = time.time()
    _write_records(
        backend,
        [{"id": f"m{i}", "text": "x", "topics": [], "cwd": None, "ts": now - i} for i in range(5)],
    )
    assert len(backend.recent(limit=2)) == 2


def test_recent_empty_when_no_records(backend):
    assert backend.recent() == []


def test_recent_returns_search_shape(backend):
    """Search shape (no score) plus the recency keys promotion orders by —
    ``ts`` was absent from the record shape in the 2026-07-04 R4 failure."""
    backend.remember("a finding", memory_id="m1", topics=["cwd:/p"])
    hit = backend.recent()[0]
    assert set(hit) == {"id", "text", "topics", "cwd", "session_id", "ts", "created_at"}
    assert isinstance(hit["ts"], float)
    assert isinstance(hit["created_at"], str)


# --------------------------------------------------------------------------
# forget (precise removal by id — the task-note-expiry correction path)
# --------------------------------------------------------------------------


def test_forget_removes_by_id(backend):
    for i in range(3):
        backend.remember(f"finding number {i}", memory_id=f"m{i}")
    assert backend.forget(["m0", "m2"]) == 2
    remaining = backend.recent(limit=10)
    assert [r["id"] for r in remaining] == ["m1"]


def test_forget_empty_ids_returns_zero(backend):
    backend.remember("keep me", memory_id="m1")
    assert backend.forget([]) == 0
    assert len(backend.recent()) == 1


def test_forget_unknown_id_keeps_all(backend):
    backend.remember("keep me", memory_id="m1")
    assert backend.forget(["nope"]) == 0
    assert len(backend.recent()) == 1


def test_forget_no_findings_file_returns_zero(backend):
    assert backend.forget(["m1"]) == 0


def test_forget_is_idempotent(backend):
    backend.remember("once", memory_id="m1")
    assert backend.forget(["m1"]) == 1
    assert backend.forget(["m1"]) == 0


def test_forget_skips_blank_and_corrupt_lines(backend):
    backend.remember("valid one", memory_id="m1")
    backend.remember("valid two", memory_id="m2")
    # Inject noise the forget scan must tolerate (mirrors prune's test).
    with backend._findings.open("a", encoding="utf-8") as fh:
        fh.write("\n")
        fh.write("{not json at all\n")
    assert backend.forget(["m1"]) == 1
    remaining = [r["id"] for r in backend.recent(limit=10)]
    assert remaining == ["m2"]


def test_forget_swallows_read_error(backend, monkeypatch):
    backend.remember("unreadable store", memory_id="m1")

    def _boom(*a, **k):
        raise OSError("disk detached")

    monkeypatch.setattr(type(backend._findings), "read_text", _boom)
    assert backend.forget(["m1"]) == 0


# --------------------------------------------------------------------------
# Truthful durable writes (cross-provider-memory-transport T1 / R1):
# a failed replace must surface as False — the 2026-07-22 Codex diagnosis
# found an unwritable sandbox fallback returning True and losing the write.
# --------------------------------------------------------------------------


def _deny_tmp_replace(monkeypatch):
    """Simulate EPERM on the findings temp file's durable replace only."""
    import errno
    from pathlib import Path

    real_replace = Path.replace

    def _eperm(self, target):
        if self.name.endswith(".jsonl.tmp"):
            raise PermissionError(errno.EPERM, "Operation not permitted")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _eperm)


def test_remember_returns_false_when_replace_denied(backend, monkeypatch):
    _deny_tmp_replace(monkeypatch)
    assert backend.remember("finding that never lands", memory_id="m1") is False
    assert backend.recent() == []  # nothing durable — and we said so


def test_eperm_through_public_stash_entry_returns_false(backend, monkeypatch):
    """R1 regression at the PUBLIC boundary: stash_entry propagates the
    backend's durable-write result and the failure reason is visible."""
    from structlog.testing import capture_logs

    import attune.memory.short_term.security as security_mod
    from attune.memory.session_stash import SessionStashEntry, stash_entry

    class _PassThroughGate:
        def __init__(self, **kwargs):
            pass

        def sanitize(self, d):
            return (d, 0)

    monkeypatch.setattr(security_mod, "DataSanitizer", _PassThroughGate)
    _deny_tmp_replace(monkeypatch)
    entry = SessionStashEntry.create(
        session_id="s1", cwd="/proj", type="note", content="sandbox canary"
    )
    with capture_logs() as logs:
        assert stash_entry(entry, backend=backend) is False
    assert any(rec.get("event") == "file_stash_write_failed" for rec in logs)


def test_forget_returns_zero_when_replace_denied(backend, monkeypatch):
    backend.remember("to delete", memory_id="m1")
    _deny_tmp_replace(monkeypatch)
    assert backend.forget(["m1"]) == 0  # deletion never landed
    monkeypatch.undo()
    assert [r["id"] for r in backend.recent()] == ["m1"]


def test_prune_returns_zero_when_replace_denied(backend, monkeypatch):
    now = time.time()
    _write_records(
        backend,
        [{"id": "old", "text": "x", "topics": [], "cwd": None, "ts": now - 5 * 86400}],
    )
    _deny_tmp_replace(monkeypatch)
    assert backend.prune(max_age_days=1) == 0  # sweep never landed


# --------------------------------------------------------------------------
# probe_write — the real writability probe backend_status relies on
# --------------------------------------------------------------------------


def test_probe_write_true_and_removes_artifact(backend):
    assert backend.probe_write() is True
    leftovers = list(backend._dir.glob(".write-probe-*"))
    assert leftovers == []


def test_probe_write_false_when_dir_is_a_file(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    be = FileStashBackend(base_dir=blocked)  # mkdir + probe both fail
    assert be.probe_write() is False
