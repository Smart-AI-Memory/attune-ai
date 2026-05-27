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
