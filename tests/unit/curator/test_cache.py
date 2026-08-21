"""Tests for the CuratorCache."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from attune.curator.cache import CuratorCache
from attune.curator.result import (
    CuratorItem,
    CuratorResult,
    SourceSummary,
    SuggestedAction,
)


def _make_result(
    *,
    summary: str = "two specs ready to close",
    cached_at: datetime | None = None,
) -> CuratorResult:
    item = CuratorItem(
        id="spec:deprecated-module-retirement",
        title="Ready to mark complete?",
        severity="nudge",
        rationale="all 3 tasks done; PR merged [spec:foo]",
        sources=["spec:foo"],
        suggested_action=SuggestedAction(
            kind="ask",
            label="Mark complete?",
            question="Mark this spec complete?",
            choices=["Yes", "Not yet", "Dismiss for 14 days"],
        ),
    )
    return CuratorResult(
        summary=summary,
        items=[item],
        sources_consulted=["specs", "bulletin"],
        cost_usd=0.08,
        cached_at=cached_at,
        model="claude-opus-4-7",
    )


@pytest.fixture
def cache_root(tmp_path) -> Path:
    return tmp_path / "curator-cache"


def test_put_then_get_returns_identical_payload(cache_root):
    cache = CuratorCache(root=cache_root)
    result = _make_result()
    cache.put("abc123", result)
    loaded = cache.get("abc123")
    assert loaded is not None
    assert loaded.summary == result.summary
    assert loaded.cost_usd == result.cost_usd
    assert loaded.model == result.model
    assert [item.id for item in loaded.items] == ["spec:deprecated-module-retirement"]
    assert loaded.items[0].suggested_action is not None
    assert loaded.items[0].suggested_action.kind == "ask"
    assert loaded.items[0].suggested_action.choices == [
        "Yes",
        "Not yet",
        "Dismiss for 14 days",
    ]


def test_get_returns_none_on_missing_key(cache_root):
    cache = CuratorCache(root=cache_root)
    assert cache.get("does-not-exist") is None


def test_ttl_expiry(cache_root):
    cache = CuratorCache(ttl_seconds=300, root=cache_root)
    # Stamp the cached_at 10 minutes in the past — well beyond TTL.
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    cache.put("abc", _make_result(cached_at=past))
    assert cache.get("abc") is None


def test_ttl_zero_is_always_stale(cache_root):
    cache = CuratorCache(ttl_seconds=0, root=cache_root)
    cache.put("abc", _make_result(cached_at=datetime.now(timezone.utc)))
    assert cache.get("abc") is None


def test_key_derives_from_source_hashes(cache_root):
    cache = CuratorCache(root=cache_root)
    s_a = [
        SourceSummary(source_id="bulletin", state_hash="aaa"),
        SourceSummary(source_id="specs", state_hash="bbb"),
    ]
    s_b = [
        SourceSummary(source_id="bulletin", state_hash="aaa"),
        SourceSummary(source_id="specs", state_hash="bbb"),
    ]
    s_c = [
        SourceSummary(source_id="bulletin", state_hash="zzz"),
        SourceSummary(source_id="specs", state_hash="bbb"),
    ]
    assert cache.key(s_a) == cache.key(s_b)
    assert cache.key(s_a) != cache.key(s_c)


def test_malformed_cache_file_returns_none(cache_root):
    cache = CuratorCache(root=cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    (cache_root / "bad.json").write_text("not-json", encoding="utf-8")
    assert cache.get("bad") is None


def test_sweep_removes_old_files(cache_root):
    cache = CuratorCache(root=cache_root)
    cache.put("fresh", _make_result())
    cache.put("ancient", _make_result())
    # Backdate "ancient" 30 days.
    ancient_path = cache_root / "ancient.json"
    target = time.time() - 30 * 86_400
    os.utime(ancient_path, (target, target))
    deleted = cache.sweep(older_than_days=7)
    assert deleted == 1
    assert (cache_root / "fresh.json").is_file()
    assert not ancient_path.exists()


def test_sweep_missing_dir_returns_zero(tmp_path):
    cache = CuratorCache(root=tmp_path / "never-created")
    assert cache.sweep(older_than_days=7) == 0


def test_key_sanitisation(cache_root):
    """Keys with shell-special chars get sanitised into safe filenames."""
    cache = CuratorCache(root=cache_root)
    cache.put("../escape/attempt", _make_result())
    files = list(cache_root.glob("*.json"))
    assert len(files) == 1
    # Sanitised name contains no path separators.
    assert "/" not in files[0].name
    assert ".." not in files[0].name


def test_properties_expose_root_and_ttl(cache_root):
    """The root and ttl_seconds properties return the configured values."""
    cache = CuratorCache(root=cache_root, ttl_seconds=600)
    assert cache.root == cache_root
    assert cache.ttl_seconds == 600


def test_empty_key_sanitises_to_default(cache_root):
    """A key with no alphanumerics falls through to 'default.json'."""
    cache = CuratorCache(root=cache_root)
    cache.put("@@@", _make_result())
    assert (cache_root / "default.json").is_file()


def test_get_returns_none_when_payload_not_dict(cache_root):
    """A JSON file whose top-level is not a dict is treated as cache miss."""
    cache_root.mkdir(parents=True, exist_ok=True)
    (cache_root / "abc.json").write_text("[1, 2, 3]", encoding="utf-8")
    cache = CuratorCache(root=cache_root)
    assert cache.get("abc") is None


def test_get_returns_none_when_cached_at_missing(cache_root):
    """A dict payload missing cached_at is a cache miss."""
    cache_root.mkdir(parents=True, exist_ok=True)
    (cache_root / "abc.json").write_text('{"summary": "x", "items": []}', encoding="utf-8")
    cache = CuratorCache(root=cache_root)
    assert cache.get("abc") is None


def test_get_returns_none_on_bad_item_schema(cache_root):
    """A cache entry whose item is missing required fields raises during
    deserialisation; the cache swallows the error and returns None."""
    cache_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": "x",
        "items": [{"id": "i1"}],  # missing 'title' — KeyError in _deserialise
        "cached_at": "2030-01-01T00:00:00+00:00",
        "cost_usd": 0.0,
        "model": "claude-opus-4-7",
        "sources_consulted": [],
    }
    import json as _json

    (cache_root / "abc.json").write_text(_json.dumps(payload), encoding="utf-8")
    cache = CuratorCache(root=cache_root, ttl_seconds=10_000_000)
    assert cache.get("abc") is None


def test_put_swallows_mkdir_failure(cache_root, monkeypatch):
    """If mkdir raises OSError, put logs and returns without writing."""
    cache = CuratorCache(root=cache_root)

    from pathlib import Path as _Path

    def boom(self, *a, **kw):  # noqa: ANN001
        raise OSError("simulated")

    monkeypatch.setattr(_Path, "mkdir", boom)
    cache.put("abc", _make_result())  # must not raise
    # No file should have been written.
    assert not any(cache_root.glob("*.json"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits; chmod is a no-op on Windows")
@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores the write bit")
def test_put_swallows_write_failure(cache_root):
    """If the atomic write fails, put logs and returns cleanly.

    The refusal is a REAL one — the cache directory is chmod'd
    unwritable — rather than a patched write method. An earlier version
    of this test monkeypatched ``Path.write_text``; when the class-G1
    fix moved the write to ``tempfile.mkstemp`` + ``os.fdopen`` the fake
    stopped firing and the test passed while asserting nothing (the
    "mock defined the contract" class). A real boundary cannot go stale
    that way.
    """
    cache_root.mkdir(parents=True, exist_ok=True)
    cache = CuratorCache(root=cache_root)

    cache_root.chmod(0o500)  # r-x: the dir cannot accept a new entry
    try:
        cache.put("abc", _make_result())  # must not raise
    finally:
        cache_root.chmod(0o700)

    assert not (cache_root / "abc.json").is_file()
    assert not any(cache_root.glob("*.tmp")), "left a temp file behind"


def test_sweep_glob_oserror_returns_zero(cache_root, monkeypatch):
    """If glob raises OSError during sweep, return 0 deletions."""
    cache_root.mkdir(parents=True, exist_ok=True)
    cache = CuratorCache(root=cache_root)

    from pathlib import Path as _Path

    def boom(self, pattern):  # noqa: ANN001
        raise OSError("simulated")

    monkeypatch.setattr(_Path, "glob", boom)
    assert cache.sweep(older_than_days=7) == 0


def test_sweep_unlink_oserror_continues(cache_root, monkeypatch):
    """If one unlink fails, sweep keeps going and counts only successes."""
    cache = CuratorCache(root=cache_root)
    cache.put("alpha", _make_result())
    cache.put("beta", _make_result())
    # Backdate both files past the sweep cutoff.
    target = time.time() - 30 * 86_400
    for path in cache_root.glob("*.json"):
        os.utime(path, (target, target))

    from pathlib import Path as _Path

    real_unlink = _Path.unlink

    def selective_boom(self, *a, **kw):  # noqa: ANN001
        if self.name == "alpha.json":
            raise OSError("simulated")
        return real_unlink(self, *a, **kw)

    monkeypatch.setattr(_Path, "unlink", selective_boom)
    deleted = cache.sweep(older_than_days=7)
    assert deleted == 1  # beta got removed; alpha's failure was swallowed
    assert (cache_root / "alpha.json").is_file()


def test_deserialise_skips_non_dict_items(cache_root):
    """Cache entries whose items[i] is not a dict get silently dropped."""
    cache_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": "x",
        "items": ["not-a-dict", {"id": "i1", "title": "t", "severity": "info"}],
        "cached_at": "2099-01-01T00:00:00+00:00",
        "cost_usd": 0.0,
        "model": "claude-opus-4-7",
        "sources_consulted": [],
    }
    import json as _json

    (cache_root / "abc.json").write_text(_json.dumps(payload), encoding="utf-8")
    cache = CuratorCache(root=cache_root, ttl_seconds=10_000_000)
    result = cache.get("abc")
    assert result is not None
    assert len(result.items) == 1  # the dict item; string was dropped


def test_deserialise_coerces_unknown_severity_to_info(cache_root):
    """An item with an unrecognised severity falls back to 'info'."""
    cache_root.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": "x",
        "items": [
            {
                "id": "i1",
                "title": "t",
                "severity": "totally-bogus",
                "rationale": "r",
                "sources": ["src"],
            }
        ],
        "cached_at": "2099-01-01T00:00:00+00:00",
        "cost_usd": 0.0,
        "model": "claude-opus-4-7",
        "sources_consulted": [],
    }
    import json as _json

    (cache_root / "abc.json").write_text(_json.dumps(payload), encoding="utf-8")
    cache = CuratorCache(root=cache_root, ttl_seconds=10_000_000)
    result = cache.get("abc")
    assert result is not None
    assert result.items[0].severity == "info"


def test_parse_iso_helpers():
    """The cache module's internal _parse_iso handles bad inputs."""
    from attune.curator.cache import _parse_iso

    assert _parse_iso("") is None
    assert _parse_iso("not-iso") is None
    # Naive ISO string -> UTC-aware datetime.
    dt = _parse_iso("2026-05-26T12:00:00")
    assert dt is not None and dt.tzinfo is not None
