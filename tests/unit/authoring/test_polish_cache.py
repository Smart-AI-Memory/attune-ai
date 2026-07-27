"""Tests for the on-disk polish cache.

Covers the cache primitives in :mod:`attune.authoring.polish`:
hit/miss, mtime bump on hit, model name participating in the
key, mtime-based pruning, the TTL=0 disable, and ``clear_cache``.

Each test uses a fresh ``tmp_path`` cache directory via the
``ATTUNE_AUTHOR_POLISH_CACHE`` env var so the user's real
``~/.attune/polish_cache`` is never touched.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the polish cache at a clean tmp directory."""
    monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE", str(tmp_path))
    # Clear any TTL override left by other tests so the default
    # (30 days) governs unless a test sets it explicitly.
    monkeypatch.delenv("ATTUNE_AUTHOR_POLISH_CACHE_TTL_SECONDS", raising=False)
    return tmp_path


class TestCachePutGet:
    """Round-trip behavior of _cache_put / _cache_get."""

    def test_put_then_get_returns_content(self, cache_dir: Path) -> None:
        from attune.authoring.polish import _cache_get, _cache_put

        _cache_put("abc", "polished content")
        assert _cache_get("abc") == "polished content"

    def test_get_returns_none_on_miss(self, cache_dir: Path) -> None:
        from attune.authoring.polish import _cache_get

        assert _cache_get("never-written") is None

    def test_put_uses_atomic_tmp_rename(self, cache_dir: Path) -> None:
        """No .tmp file should remain after a successful put."""
        from attune.authoring.polish import _cache_put

        _cache_put("abc", "x")
        leftovers = list(cache_dir.glob("*.tmp"))
        assert leftovers == [], f"orphaned .tmp files: {leftovers}"

    def test_get_bumps_mtime(self, cache_dir: Path) -> None:
        """A cache hit must update the entry's mtime so the prune
        sweeper treats it as hot. Verified by stamping an ancient
        mtime, hitting the cache, then confirming mtime advanced.
        """
        from attune.authoring.polish import _cache_get, _cache_put

        _cache_put("hot", "content")
        path = next(cache_dir.glob("*.md"))
        ancient = time.time() - 10_000
        os.utime(path, (ancient, ancient))

        _cache_get("hot")

        new_mtime = path.stat().st_mtime
        assert new_mtime > ancient + 100, f"mtime did not bump on hit: {new_mtime - ancient}s delta"


class TestCacheKeyIncludesModel:
    """The model name must participate in the cache key so a model
    bump in attune-author invalidates entries automatically.
    """

    def test_model_change_invalidates_cache(self, cache_dir: Path) -> None:
        """Changing the resolved polish model (via the premium-tier env
        pin) produces a different key for the same
        content/summary/template_type/system_prompt/context.
        """
        from attune.authoring import polish

        # First call with one model pin produces a key K1. The pins are
        # unknown model ids — resolve_model honors them with a warning.
        with patch("attune.authoring.polish._call_llm", return_value="from old"):
            with patch.dict(
                "os.environ",
                {
                    "ANTHROPIC_API_KEY": "fake",  # pragma: allowlist secret
                    "ATTUNE_MODEL_PREMIUM": "claude-old",
                },
            ):
                out_old = polish.polish_template("# T", "feat", "sum", template_type="concept")
        assert out_old.startswith("from old")

        # Second call with a different model must miss the cache —
        # the LLM mock returns a different value, which we observe.
        with patch("attune.authoring.polish._call_llm", return_value="from new"):
            with patch.dict(
                "os.environ",
                {
                    "ANTHROPIC_API_KEY": "fake",  # pragma: allowlist secret
                    "ATTUNE_MODEL_PREMIUM": "claude-new",
                },
            ):
                out_new = polish.polish_template("# T", "feat", "sum", template_type="concept")
        assert out_new.startswith(
            "from new"
        ), "model change should invalidate cache key, but a stale entry was served"


class TestCachePrune:
    """Mtime-based pruning behavior."""

    def test_prune_deletes_stale_entries(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.authoring.polish import _cache_prune, _cache_put

        monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE_TTL_SECONDS", "1")
        _cache_put("a", "alpha")
        _cache_put("b", "beta")
        # Backdate one entry past the TTL.
        for path in cache_dir.glob("*.md"):
            if "a" in path.name:
                continue  # leave 'a' fresh — file name is the sha256, so this
                # branch never matches; we instead pick the first entry below
        # Pick the first .md and backdate it.
        targets = sorted(cache_dir.glob("*.md"))
        old_path = targets[0]
        ancient = time.time() - 10_000
        os.utime(old_path, (ancient, ancient))

        deleted = _cache_prune()

        assert deleted == 1
        assert not old_path.exists()
        # The other entry survives.
        survivors = list(cache_dir.glob("*.md"))
        assert len(survivors) == 1

    def test_prune_with_ttl_zero_disables(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.authoring.polish import _cache_prune, _cache_put

        monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE_TTL_SECONDS", "0")
        _cache_put("a", "alpha")
        ancient = time.time() - 10_000
        for path in cache_dir.glob("*.md"):
            os.utime(path, (ancient, ancient))

        assert _cache_prune() == 0
        # Entry survives despite being ancient.
        assert list(cache_dir.glob("*.md"))

    def test_prune_handles_missing_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.authoring.polish import _cache_prune

        nonexistent = tmp_path / "does-not-exist"
        monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE", str(nonexistent))
        assert _cache_prune() == 0

    def test_invalid_ttl_falls_back_to_default(
        self, cache_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Unparseable / negative TTL must NOT disable the cache —
        the prune should fall back to the 30-day default. We verify
        by stamping an entry one hour old; default TTL leaves it.
        """
        from attune.authoring.polish import _cache_prune, _cache_put

        monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE_TTL_SECONDS", "garbage")
        _cache_put("a", "alpha")
        an_hour_ago = time.time() - 3600
        for path in cache_dir.glob("*.md"):
            os.utime(path, (an_hour_ago, an_hour_ago))

        assert _cache_prune() == 0
        assert list(cache_dir.glob("*.md")), "fresh entry was wrongly pruned"


class TestClearCache:
    """clear_cache() removes all entries unconditionally."""

    def test_clear_removes_all_md_and_tmp(self, cache_dir: Path) -> None:
        from attune.authoring.polish import _cache_put, clear_cache

        _cache_put("a", "alpha")
        _cache_put("b", "beta")
        # Drop a stray .tmp simulating an interrupted write.
        (cache_dir / "interrupted.tmp").write_text("partial")

        # And an unrelated file that must NOT be deleted.
        (cache_dir / "README.txt").write_text("don't touch me")

        deleted = clear_cache()

        assert deleted == 3
        assert not list(cache_dir.glob("*.md"))
        assert not list(cache_dir.glob("*.tmp"))
        assert (cache_dir / "README.txt").exists()

    def test_clear_handles_missing_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from attune.authoring.polish import clear_cache

        nonexistent = tmp_path / "does-not-exist"
        monkeypatch.setenv("ATTUNE_AUTHOR_POLISH_CACHE", str(nonexistent))
        assert clear_cache() == 0


class TestPolishTemplateCacheIntegration:
    """End-to-end: polish_template hits the cache on a second call."""

    def test_second_call_uses_cache_and_skips_llm(self, cache_dir: Path) -> None:
        from attune.authoring import polish

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "fake"},  # pragma: allowlist secret
        ):
            with patch(
                "attune.authoring.polish._call_llm",
                return_value="polished output",
            ) as mock_llm:
                first = polish.polish_template("# T", "feat", "sum", template_type="concept")
                second = polish.polish_template("# T", "feat", "sum", template_type="concept")

        assert first == second
        # The LLM must have been called exactly once — the second
        # call is served from the on-disk cache.
        assert mock_llm.call_count == 1

    def test_volatile_generated_at_does_not_invalidate_cache(self, cache_dir: Path) -> None:
        """Regression test for the 0.6.0 bug: the rendered template
        embeds a fresh ``generated_at`` timestamp on every render,
        which made the cache key change every time and the cache
        never hit. Two renders that differ ONLY in generated_at
        must share a cache entry.
        """
        from attune.authoring import polish

        first_render = (
            "---\n"
            "type: concept\n"
            "feature: foo\n"
            "generated_at: 2026-05-01T10:00:00.000000+00:00\n"
            "source_hash: abc\n"
            "---\n\n"
            "# Foo\n"
        )
        second_render = first_render.replace("10:00:00", "12:34:56")
        assert first_render != second_render  # sanity: timestamps differ

        with patch.dict(
            "os.environ",
            {"ANTHROPIC_API_KEY": "fake"},  # pragma: allowlist secret
        ):
            with patch(
                "attune.authoring.polish._call_llm",
                return_value="polished",
            ) as mock_llm:
                polish.polish_template(first_render, "foo", "sum", template_type="concept")
                polish.polish_template(second_render, "foo", "sum", template_type="concept")

        assert (
            mock_llm.call_count == 1
        ), "second render with different generated_at should have hit cache"

    def test_normalize_for_key_strips_generated_at(self) -> None:
        """Unit-level check on the normalizer used to build the key."""
        from attune.authoring.polish import _normalize_for_key

        a = "type: concept\ngenerated_at: 2026-05-01T10:00:00+00:00\nsource_hash: x\n"
        b = "type: concept\ngenerated_at: 2026-05-01T11:11:11+00:00\nsource_hash: x\n"
        assert _normalize_for_key(a) == _normalize_for_key(b)
        # Other fields must NOT be stripped — changing source_hash
        # is a real input change and must produce a different key.
        c = "type: concept\ngenerated_at: 2026-05-01T10:00:00+00:00\nsource_hash: DIFFERENT\n"
        assert _normalize_for_key(a) != _normalize_for_key(c)
