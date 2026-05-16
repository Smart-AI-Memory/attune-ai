"""Tests for the on-disk session-summary cache.

Covers cache-key computation (last-4KB SHA-256), load/save round-trip,
and the cache-invalidation matrix: any of (filename, mtime, content
tail) drifting must produce a miss.
"""

from __future__ import annotations

import json
import time

import pytest

from attune.ops import session_summary_cache as cache


def test_cache_key_filename_is_basename(tmp_path):
    p = tmp_path / "abc12345.jsonl"
    p.write_text("hello", encoding="utf-8")
    key = cache.compute_cache_key(p)
    assert key is not None
    assert key.filename == "abc12345.jsonl"


def test_cache_key_short_file_hashes_whole_file(tmp_path):
    p = tmp_path / "short.jsonl"
    p.write_text("hi", encoding="utf-8")
    key = cache.compute_cache_key(p)
    assert key is not None
    # Manually compute expected
    import hashlib

    expected = hashlib.sha256(b"hi").hexdigest()
    assert key.sha256 == expected


def test_cache_key_long_file_hashes_only_tail(tmp_path):
    """Files larger than the tail size hash only the last 4 KiB."""
    p = tmp_path / "long.jsonl"
    head = b"H" * 10_000
    tail = b"T" * 4096  # exactly the tail-window size
    p.write_bytes(head + tail)

    key = cache.compute_cache_key(p)
    assert key is not None

    import hashlib

    expected = hashlib.sha256(tail).hexdigest()
    assert key.sha256 == expected


def test_cache_key_tail_changes_when_content_grows(tmp_path):
    """Appending content (the typical JSONL growth pattern) flips the tail hash."""
    p = tmp_path / "growing.jsonl"
    p.write_text("a" * 5000, encoding="utf-8")
    key1 = cache.compute_cache_key(p)
    # Wait one tick so mtime moves too — though the tail hash alone
    # should already differ.
    time.sleep(0.01)
    with p.open("a", encoding="utf-8") as fh:
        fh.write("b" * 1000)
    key2 = cache.compute_cache_key(p)
    assert key1 is not None and key2 is not None
    assert key1.sha256 != key2.sha256


def test_compute_cache_key_returns_none_for_missing_file(tmp_path):
    assert cache.compute_cache_key(tmp_path / "nope.jsonl") is None


# ---------------------------------------------------------------------------
# load / save round-trip
# ---------------------------------------------------------------------------


@pytest.fixture
def attune_home(tmp_path):
    return tmp_path / "attune-home"


def _make_key():
    return cache.CacheKey(
        filename="abc.jsonl",
        mtime_ns=1_700_000_000_000_000_000,
        sha256="deadbeef" * 8,
    )


def test_save_and_load_round_trip(attune_home):
    key = _make_key()
    path = cache.save(
        attune_home,
        "session-id-1",
        key=key,
        summary="A redacted summary.",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.0012,
    )
    assert path.exists()

    loaded = cache.load(attune_home, "session-id-1", expected=key)
    assert loaded is not None
    assert loaded.summary == "A redacted summary."
    assert loaded.tokens_in == 100
    assert loaded.tokens_out == 50
    assert loaded.cost_usd == pytest.approx(0.0012)
    # Source on hit is "cached", not "haiku".
    assert loaded.source == "cached"
    assert loaded.created_at  # non-empty ISO string


def test_load_returns_none_when_file_missing(attune_home):
    assert cache.load(attune_home, "no-such-id", expected=_make_key()) is None


def test_load_returns_none_on_filename_mismatch(attune_home):
    saved_key = _make_key()
    cache.save(
        attune_home,
        "sid",
        key=saved_key,
        summary="x",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.0,
    )
    drifted = cache.CacheKey(
        filename="other.jsonl", mtime_ns=saved_key.mtime_ns, sha256=saved_key.sha256
    )
    assert cache.load(attune_home, "sid", expected=drifted) is None


def test_load_returns_none_on_mtime_mismatch(attune_home):
    saved_key = _make_key()
    cache.save(
        attune_home,
        "sid",
        key=saved_key,
        summary="x",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.0,
    )
    drifted = cache.CacheKey(
        filename=saved_key.filename, mtime_ns=saved_key.mtime_ns + 1, sha256=saved_key.sha256
    )
    assert cache.load(attune_home, "sid", expected=drifted) is None


def test_load_returns_none_on_sha_mismatch(attune_home):
    saved_key = _make_key()
    cache.save(
        attune_home,
        "sid",
        key=saved_key,
        summary="x",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.0,
    )
    drifted = cache.CacheKey(
        filename=saved_key.filename, mtime_ns=saved_key.mtime_ns, sha256="0" * 64
    )
    assert cache.load(attune_home, "sid", expected=drifted) is None


def test_load_returns_none_on_malformed_json(attune_home):
    path = cache.cache_path_for(attune_home, "sid")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json{{{", encoding="utf-8")
    assert cache.load(attune_home, "sid", expected=_make_key()) is None


def test_save_is_atomic_no_temp_files_left_behind(attune_home):
    """After a successful save, only the final ``.json`` file should
    exist in the cache dir — no ``.tmp`` siblings."""
    key = _make_key()
    cache.save(
        attune_home,
        "sid",
        key=key,
        summary="x",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.0,
    )
    cache_dir = attune_home / "ops" / "session_summaries"
    leftover_tmp = list(cache_dir.glob(".sid.*.tmp"))
    assert leftover_tmp == [], f"temp files leaked: {leftover_tmp}"


def test_cache_path_for_does_not_create_dir(attune_home):
    """Computing the path must not have side effects on the filesystem."""
    path = cache.cache_path_for(attune_home, "sid")
    assert not path.parent.exists()
    assert not path.exists()


def test_save_persisted_record_has_haiku_source_on_disk(attune_home):
    """The on-disk JSON records ``source: "haiku"`` even though
    ``load()`` reports ``cached`` to callers — so a future reader can
    distinguish "fresh write" from "cache hit" by inspecting the file."""
    cache.save(
        attune_home,
        "sid",
        key=_make_key(),
        summary="x",
        tokens_in=1,
        tokens_out=1,
        cost_usd=0.0,
    )
    path = cache.cache_path_for(attune_home, "sid")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["source"] == "haiku"
