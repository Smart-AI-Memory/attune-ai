"""Tests for CacheManager — local LRU cache layer.

Pure-Python class with no Redis / SDK dependency. Targets every
branch including the LRU eviction path (cache full → drop oldest
by last_access).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import time

import pytest

from attune.memory.short_term.caching import CacheManager


@pytest.fixture
def cache() -> CacheManager:
    """Fresh enabled cache with default size."""
    return CacheManager(enabled=True, max_size=1000)


@pytest.fixture
def small_cache() -> CacheManager:
    """Small cache for LRU-eviction scenarios."""
    return CacheManager(enabled=True, max_size=3)


@pytest.fixture
def disabled_cache() -> CacheManager:
    """Disabled cache to exercise the early-return branches."""
    return CacheManager(enabled=False, max_size=1000)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestInit:
    def test_defaults(self):
        c = CacheManager()
        assert c.enabled is True
        assert c.max_size == 1000
        assert c.hits == 0
        assert c.misses == 0
        assert len(c) == 0

    def test_custom_size(self):
        c = CacheManager(enabled=True, max_size=42)
        assert c.max_size == 42

    def test_disabled_construction(self):
        c = CacheManager(enabled=False)
        assert c.enabled is False


# ---------------------------------------------------------------------------
# get() / add() — happy path
# ---------------------------------------------------------------------------


class TestGetAdd:
    def test_get_miss_returns_none(self, cache):
        assert cache.get("absent") is None
        assert cache.misses == 1
        assert cache.hits == 0

    def test_add_then_get_returns_value(self, cache):
        cache.add("k", "v")
        assert cache.get("k") == "v"
        assert cache.hits == 1
        assert cache.misses == 0

    def test_get_updates_last_access(self, cache):
        """Hit should update last_access (LRU tracking)."""
        cache.add("k", "v")
        first_access = cache._cache["k"][2]
        time.sleep(0.001)  # ensure clock tick
        cache.get("k")
        second_access = cache._cache["k"][2]
        assert second_access >= first_access

    def test_add_stores_timestamp_and_access(self, cache):
        cache.add("k", "v")
        value, timestamp, last_access = cache._cache["k"]
        assert value == "v"
        assert timestamp > 0
        assert last_access == timestamp  # initially equal


# ---------------------------------------------------------------------------
# get() / add() — disabled branches
# ---------------------------------------------------------------------------


class TestDisabledBranches:
    def test_get_when_disabled_returns_none(self, disabled_cache):
        disabled_cache._cache["k"] = ("v", time.time(), time.time())
        assert disabled_cache.get("k") is None
        assert disabled_cache.misses == 1

    def test_add_when_disabled_is_noop(self, disabled_cache):
        disabled_cache.add("k", "v")
        assert "k" not in disabled_cache._cache
        assert len(disabled_cache) == 0

    def test_contains_when_disabled_returns_false(self, disabled_cache):
        disabled_cache._cache["k"] = ("v", time.time(), time.time())
        assert disabled_cache.contains("k") is False
        assert "k" not in disabled_cache  # via __contains__


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------


class TestLRUEviction:
    def test_eviction_drops_oldest_access(self, small_cache):
        """Filling beyond capacity drops the least-recently-accessed entry."""
        small_cache.add("a", "1")
        time.sleep(0.001)
        small_cache.add("b", "2")
        time.sleep(0.001)
        small_cache.add("c", "3")
        # All three present.
        assert len(small_cache) == 3

        # Touch "a" so it's the most-recently-accessed.
        time.sleep(0.001)
        small_cache.get("a")

        # Adding a 4th should evict "b" (oldest last_access now).
        time.sleep(0.001)
        small_cache.add("d", "4")
        assert "a" in small_cache
        assert "b" not in small_cache
        assert "c" in small_cache
        assert "d" in small_cache
        assert len(small_cache) == 3

    def test_eviction_at_exact_capacity(self, small_cache):
        """Adding when len == max_size triggers eviction even on first overflow."""
        small_cache.add("a", "1")
        small_cache.add("b", "2")
        small_cache.add("c", "3")
        assert len(small_cache) == small_cache.max_size

        small_cache.add("d", "4")
        assert len(small_cache) == 3
        # Some original key was dropped.
        kept = {k for k in ("a", "b", "c") if k in small_cache}
        assert len(kept) == 2


# ---------------------------------------------------------------------------
# remove() / invalidate()
# ---------------------------------------------------------------------------


class TestRemove:
    def test_remove_present_key(self, cache):
        cache.add("k", "v")
        assert cache.remove("k") is True
        assert "k" not in cache._cache

    def test_remove_absent_key(self, cache):
        assert cache.remove("absent") is False

    def test_invalidate_is_alias_for_remove(self, cache):
        cache.add("k", "v")
        assert cache.invalidate("k") is True
        assert cache.invalidate("k") is False  # already gone


# ---------------------------------------------------------------------------
# contains() / __contains__
# ---------------------------------------------------------------------------


class TestContains:
    def test_contains_present_key(self, cache):
        cache.add("k", "v")
        assert cache.contains("k") is True
        assert "k" in cache  # __contains__

    def test_contains_absent_key(self, cache):
        assert cache.contains("absent") is False
        assert "absent" not in cache

    def test_contains_does_not_touch_counters(self, cache):
        """contains() must NOT increment hits/misses."""
        cache.add("k", "v")
        cache.contains("k")
        cache.contains("absent")
        assert cache.hits == 0
        assert cache.misses == 0


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


class TestClear:
    def test_clear_returns_count(self, cache):
        cache.add("a", "1")
        cache.add("b", "2")
        cache.add("c", "3")
        assert cache.clear() == 3
        assert len(cache) == 0

    def test_clear_empty_returns_zero(self, cache):
        assert cache.clear() == 0

    def test_clear_resets_counters(self, cache):
        cache.add("k", "v")
        cache.get("k")  # hit
        cache.get("nope")  # miss
        cache.clear()
        assert cache.hits == 0
        assert cache.misses == 0


# ---------------------------------------------------------------------------
# get_stats()
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_empty_cache_stats(self, cache):
        stats = cache.get_stats()
        assert stats["enabled"] is True
        assert stats["size"] == 0
        assert stats["max_size"] == 1000
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 0

    def test_hit_rate_with_traffic(self, cache):
        cache.add("k", "v")
        cache.get("k")  # hit
        cache.get("k")  # hit
        cache.get("absent")  # miss
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == pytest.approx(66.666666, rel=1e-3)

    def test_stats_reflect_disabled_state(self, disabled_cache):
        stats = disabled_cache.get_stats()
        assert stats["enabled"] is False

    def test_zero_requests_hit_rate_is_zero(self, cache):
        """Division-by-zero guard: 0 total requests → 0.0% hit rate."""
        stats = cache.get_stats()
        assert stats["hit_rate"] == 0.0


# ---------------------------------------------------------------------------
# Dunders
# ---------------------------------------------------------------------------


class TestDunders:
    def test_len_grows_with_adds(self, cache):
        assert len(cache) == 0
        cache.add("a", "1")
        assert len(cache) == 1
        cache.add("b", "2")
        assert len(cache) == 2

    def test_len_after_remove(self, cache):
        cache.add("a", "1")
        cache.remove("a")
        assert len(cache) == 0

    def test_contains_dunder_routes_through_method(self, cache):
        cache.add("a", "1")
        assert ("a" in cache) is True
        assert ("b" in cache) is False
