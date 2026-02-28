"""Unit tests for HashOnlyCache - hash-based exact-match caching.

This test suite provides comprehensive coverage for the hash-only cache
implementation, including initialization, get/put operations, expiration,
LRU eviction, and statistics tracking.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import time
from unittest.mock import patch

import pytest

from attune.cache.hash_only import HashOnlyCache


@pytest.mark.unit
class TestHashOnlyCacheInitialization:
    """Test suite for HashOnlyCache initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        cache = HashOnlyCache()

        assert cache.max_memory_mb == 100
        assert cache.default_ttl == 86400
        assert cache._memory_cache == {}
        assert cache._access_times == {}

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        cache = HashOnlyCache(
            max_size_mb=1000,
            default_ttl=3600,
            max_memory_mb=200,
        )

        assert cache.max_memory_mb == 200
        assert cache.default_ttl == 3600
        assert cache._memory_cache == {}
        assert cache._access_times == {}

    def test_init_creates_cache_stats(self):
        """Test that initialization creates cache statistics."""
        cache = HashOnlyCache()

        assert hasattr(cache, "stats")
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0
        assert cache.stats.evictions == 0


@pytest.mark.unit
class TestHashOnlyCacheGetOperations:
    """Test suite for HashOnlyCache get operations."""

    def test_get_cache_miss_on_first_call(self):
        """Test that first get call results in cache miss."""
        cache = HashOnlyCache()

        result = cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        assert result is None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_get_cache_hit_on_second_call(self):
        """Test that second get call with same params results in cache hit."""
        cache = HashOnlyCache()

        # First call - put response in cache
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "cached response"},
        )

        # Reset stats to test hit
        cache.stats.misses = 0

        # Second call - should hit cache
        result = cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        assert result == {"content": "cached response"}
        assert cache.stats.hits == 1
        assert cache.stats.misses == 0

    def test_get_updates_access_time_on_hit(self):
        """Test that get updates access time on cache hit."""
        cache = HashOnlyCache()

        # Put entry in cache
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "cached response"},
        )

        # Get cache key
        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )
        original_access_time = cache._access_times[cache_key]

        # Wait a bit
        time.sleep(0.01)

        # Get from cache
        cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        # Access time should be updated
        new_access_time = cache._access_times[cache_key]
        assert new_access_time > original_access_time

    def test_get_returns_none_for_expired_entry(self):
        """Test that get returns None for expired cache entry."""
        cache = HashOnlyCache(default_ttl=1)  # 1 second TTL

        # Put entry in cache
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "cached response"},
        )

        # Wait for expiration
        time.sleep(1.1)

        # Get should return None (expired)
        result = cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        assert result is None
        assert cache.stats.misses == 1

    def test_get_evicts_expired_entry(self):
        """Test that get evicts expired entry from cache."""
        cache = HashOnlyCache(default_ttl=1)  # 1 second TTL

        # Put entry in cache
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "cached response"},
        )

        # Verify entry exists
        assert len(cache._memory_cache) == 1

        # Wait for expiration
        time.sleep(1.1)

        # Get should evict expired entry
        cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        # Entry should be evicted
        assert len(cache._memory_cache) == 0
        assert cache.stats.evictions == 1

    def test_get_cache_miss_for_different_prompt(self):
        """Test that get returns cache miss for different prompt."""
        cache = HashOnlyCache()

        # Put entry with prompt A
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="prompt A",
            model="claude-3-5-sonnet",
            response={"content": "response A"},
        )

        # Get with prompt B should miss
        result = cache.get(
            workflow="test-workflow",
            stage="test-stage",
            prompt="prompt B",
            model="claude-3-5-sonnet",
        )

        assert result is None
        assert cache.stats.misses == 1

    def test_get_cache_miss_for_different_workflow(self):
        """Test that get returns cache miss for different workflow."""
        cache = HashOnlyCache()

        # Put entry for workflow A
        cache.put(
            workflow="workflow-a",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "response A"},
        )

        # Get for workflow B should miss
        result = cache.get(
            workflow="workflow-b",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
        )

        assert result is None
        assert cache.stats.misses == 1


@pytest.mark.unit
class TestHashOnlyCachePutOperations:
    """Test suite for HashOnlyCache put operations."""

    def test_put_stores_response_in_memory(self):
        """Test that put stores response in memory cache."""
        cache = HashOnlyCache()

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        assert len(cache._memory_cache) == 1

    def test_put_creates_cache_entry_with_metadata(self):
        """Test that put creates cache entry with correct metadata."""
        cache = HashOnlyCache()

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        # Get the cache key
        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )

        entry = cache._memory_cache[cache_key]
        assert entry.workflow == "test-workflow"
        assert entry.stage == "test-stage"
        assert entry.model == "claude-3-5-sonnet"
        assert entry.response == {"content": "test response"}

    def test_put_uses_custom_ttl(self):
        """Test that put respects custom TTL parameter."""
        cache = HashOnlyCache(default_ttl=86400)

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
            ttl=3600,  # Custom TTL
        )

        # Get the cache key
        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )

        entry = cache._memory_cache[cache_key]
        assert entry.ttl == 3600

    def test_put_uses_default_ttl_when_not_specified(self):
        """Test that put uses default TTL when not specified."""
        cache = HashOnlyCache(default_ttl=7200)

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        # Get the cache key
        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )

        entry = cache._memory_cache[cache_key]
        assert entry.ttl == 7200

    def test_put_sets_access_time(self):
        """Test that put sets access time for entry."""
        cache = HashOnlyCache()

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        # Get the cache key
        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )

        assert cache_key in cache._access_times
        assert cache._access_times[cache_key] > 0

    @patch("attune.cache.hash_only.HashOnlyCache._maybe_evict_lru")
    def test_put_triggers_lru_eviction_check(self, mock_evict):
        """Test that put triggers LRU eviction check."""
        cache = HashOnlyCache()

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        mock_evict.assert_called_once()


@pytest.mark.unit
class TestHashOnlyCacheLRUEviction:
    """Test suite for HashOnlyCache LRU eviction."""

    def test_maybe_evict_lru_does_nothing_when_under_limit(self):
        """Test that LRU eviction does nothing when under memory limit."""
        cache = HashOnlyCache(max_memory_mb=100)

        # Add a few entries (well under limit)
        for i in range(10):
            cache.put(
                workflow="test-workflow",
                stage="test-stage",
                prompt=f"prompt {i}",
                model="claude-3-5-sonnet",
                response={"content": f"response {i}"},
            )

        # All entries should still be in cache
        assert len(cache._memory_cache) == 10
        assert cache.stats.evictions == 0

    def test_maybe_evict_lru_evicts_when_over_limit(self):
        """Test that LRU eviction removes entries when over memory limit."""
        cache = HashOnlyCache(max_memory_mb=1)  # Very small limit

        # Add enough entries to trigger eviction
        for i in range(200):  # 200 * 0.01MB = 2MB > 1MB limit
            cache.put(
                workflow="test-workflow",
                stage="test-stage",
                prompt=f"prompt {i}",
                model="claude-3-5-sonnet",
                response={"content": f"response {i}"},
            )

        # Should have evicted some entries
        assert len(cache._memory_cache) < 200
        assert cache.stats.evictions > 0

    def test_maybe_evict_lru_evicts_oldest_entries(self):
        """Test that LRU eviction removes least recently used entries."""
        cache = HashOnlyCache(max_memory_mb=1)

        # Add first entry
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="old prompt",
            model="claude-3-5-sonnet",
            response={"content": "old response"},
        )

        time.sleep(0.01)

        # Add many more entries to trigger eviction
        for i in range(200):
            cache.put(
                workflow="test-workflow",
                stage="test-stage",
                prompt=f"prompt {i}",
                model="claude-3-5-sonnet",
                response={"content": f"response {i}"},
            )

        # Old entry should be evicted (LRU)
        old_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "old prompt",
            "claude-3-5-sonnet",
        )
        assert old_key not in cache._memory_cache

    def test_evict_entry_removes_from_memory_and_access_times(self):
        """Test that evict_entry removes from both dictionaries."""
        cache = HashOnlyCache()

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        cache_key = cache._create_cache_key(
            "test-workflow",
            "test-stage",
            "test prompt",
            "claude-3-5-sonnet",
        )

        # Verify entry exists
        assert cache_key in cache._memory_cache
        assert cache_key in cache._access_times

        # Evict entry
        cache._evict_entry(cache_key)

        # Entry should be removed from both
        assert cache_key not in cache._memory_cache
        assert cache_key not in cache._access_times
        assert cache.stats.evictions == 1

    def test_evict_entry_handles_missing_key_gracefully(self):
        """Test that evict_entry handles missing key without error."""
        cache = HashOnlyCache()

        # Try to evict non-existent key
        cache._evict_entry("non-existent-key")

        # Should increment evictions but not crash
        assert cache.stats.evictions == 1


@pytest.mark.unit
class TestHashOnlyCacheExpiration:
    """Test suite for HashOnlyCache TTL expiration."""

    def test_evict_expired_removes_expired_entries(self):
        """Test that evict_expired removes all expired entries."""
        cache = HashOnlyCache(default_ttl=1)  # 1 second TTL

        # Add entries
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="prompt 1",
            model="claude-3-5-sonnet",
            response={"content": "response 1"},
        )

        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="prompt 2",
            model="claude-3-5-sonnet",
            response={"content": "response 2"},
        )

        # Wait for expiration
        time.sleep(1.1)

        # Evict expired
        evicted_count = cache.evict_expired()

        assert evicted_count == 2
        assert len(cache._memory_cache) == 0

    def test_evict_expired_keeps_valid_entries(self):
        """Test that evict_expired keeps non-expired entries."""
        cache = HashOnlyCache(default_ttl=60)  # 60 second TTL

        # Add entries
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="prompt 1",
            model="claude-3-5-sonnet",
            response={"content": "response 1"},
        )

        # Evict expired (none should be expired)
        evicted_count = cache.evict_expired()

        assert evicted_count == 0
        assert len(cache._memory_cache) == 1

    def test_evict_expired_returns_zero_when_no_expired(self):
        """Test that evict_expired returns 0 when no entries are expired."""
        cache = HashOnlyCache(default_ttl=3600)

        # Add entry
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        # Evict expired
        evicted_count = cache.evict_expired()

        assert evicted_count == 0


@pytest.mark.unit
class TestHashOnlyCacheClearAndStats:
    """Test suite for HashOnlyCache clear and stats operations."""

    def test_clear_removes_all_entries(self):
        """Test that clear removes all cache entries."""
        cache = HashOnlyCache()

        # Add multiple entries
        for i in range(10):
            cache.put(
                workflow="test-workflow",
                stage="test-stage",
                prompt=f"prompt {i}",
                model="claude-3-5-sonnet",
                response={"content": f"response {i}"},
            )

        # Clear cache
        cache.clear()

        assert len(cache._memory_cache) == 0
        assert len(cache._access_times) == 0

    def test_clear_removes_access_times(self):
        """Test that clear removes all access times."""
        cache = HashOnlyCache()

        # Add entry
        cache.put(
            workflow="test-workflow",
            stage="test-stage",
            prompt="test prompt",
            model="claude-3-5-sonnet",
            response={"content": "test response"},
        )

        assert len(cache._access_times) == 1

        # Clear cache
        cache.clear()

        assert len(cache._access_times) == 0

    def test_get_stats_returns_cache_statistics(self):
        """Test that get_stats returns CacheStats object."""
        cache = HashOnlyCache()

        # Perform some operations
        cache.put("wf", "stage", "prompt1", "model", {"content": "resp1"})
        cache.get("wf", "stage", "prompt1", "model")  # Hit
        cache.get("wf", "stage", "prompt2", "model")  # Miss

        stats = cache.get_stats()

        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 50.0

    def test_size_info_returns_cache_size_metrics(self):
        """Test that size_info returns cache size information."""
        cache = HashOnlyCache(max_memory_mb=100)

        # Add entries
        for i in range(50):
            cache.put(
                workflow="test-workflow",
                stage="test-stage",
                prompt=f"prompt {i}",
                model="claude-3-5-sonnet",
                response={"content": f"response {i}"},
            )

        size_info = cache.size_info()

        assert size_info["entries"] == 50
        assert size_info["estimated_mb"] == 50 * 0.01  # 0.5 MB
        assert size_info["max_memory_mb"] == 100

    def test_size_info_returns_zero_for_empty_cache(self):
        """Test that size_info returns 0 entries for empty cache."""
        cache = HashOnlyCache()

        size_info = cache.size_info()

        assert size_info["entries"] == 0
        assert size_info["estimated_mb"] == 0


@pytest.mark.unit
class TestHashOnlyCacheEdgeCases:
    """Test suite for HashOnlyCache edge cases."""

    def test_multiple_workflows_in_same_cache(self):
        """Test that cache handles multiple workflows correctly."""
        cache = HashOnlyCache()

        # Add entries for different workflows
        cache.put("workflow-a", "stage", "prompt", "model", {"content": "response-a"})
        cache.put("workflow-b", "stage", "prompt", "model", {"content": "response-b"})

        # Retrieve entries
        result_a = cache.get("workflow-a", "stage", "prompt", "model")
        result_b = cache.get("workflow-b", "stage", "prompt", "model")

        assert result_a == {"content": "response-a"}
        assert result_b == {"content": "response-b"}

    def test_multiple_stages_in_same_workflow(self):
        """Test that cache handles multiple stages correctly."""
        cache = HashOnlyCache()

        # Add entries for different stages
        cache.put("workflow", "stage-a", "prompt", "model", {"content": "response-a"})
        cache.put("workflow", "stage-b", "prompt", "model", {"content": "response-b"})

        # Retrieve entries
        result_a = cache.get("workflow", "stage-a", "prompt", "model")
        result_b = cache.get("workflow", "stage-b", "prompt", "model")

        assert result_a == {"content": "response-a"}
        assert result_b == {"content": "response-b"}

    def test_multiple_models_for_same_prompt(self):
        """Test that cache handles different models correctly."""
        cache = HashOnlyCache()

        # Add entries for different models
        cache.put("workflow", "stage", "prompt", "claude-3-5-sonnet", {"content": "sonnet"})
        cache.put("workflow", "stage", "prompt", "claude-3-haiku", {"content": "haiku"})

        # Retrieve entries
        result_sonnet = cache.get("workflow", "stage", "prompt", "claude-3-5-sonnet")
        result_haiku = cache.get("workflow", "stage", "prompt", "claude-3-haiku")

        assert result_sonnet == {"content": "sonnet"}
        assert result_haiku == {"content": "haiku"}

    def test_cache_handles_complex_response_objects(self):
        """Test that cache stores and retrieves complex objects."""
        cache = HashOnlyCache()

        complex_response = {
            "content": "detailed response",
            "metadata": {"tokens": 100, "cost": 0.05},
            "usage": {"input": 50, "output": 50},
            "nested": {"data": [1, 2, 3]},
        }

        cache.put("workflow", "stage", "prompt", "model", complex_response)
        result = cache.get("workflow", "stage", "prompt", "model")

        assert result == complex_response

    def test_cache_handles_empty_prompt(self):
        """Test that cache handles empty prompt string."""
        cache = HashOnlyCache()

        cache.put("workflow", "stage", "", "model", {"content": "response"})
        result = cache.get("workflow", "stage", "", "model")

        assert result == {"content": "response"}

    def test_cache_handles_very_long_prompt(self):
        """Test that cache handles very long prompts."""
        cache = HashOnlyCache()

        long_prompt = "x" * 10000  # 10K characters

        cache.put("workflow", "stage", long_prompt, "model", {"content": "response"})
        result = cache.get("workflow", "stage", long_prompt, "model")

        assert result == {"content": "response"}
