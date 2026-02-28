"""Unit tests for CacheStorage.

Tests disk persistence, TTL expiration, and storage management.
"""

import json
import tempfile
import time
from pathlib import Path

from attune.cache.base import CacheEntry
from attune.cache.storage import CacheStorage


class TestCacheStorage:
    """Test suite for CacheStorage."""

    def test_init_creates_cache_dir(self):
        """Test that cache directory is created on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            CacheStorage(cache_dir=cache_dir)

            assert cache_dir.exists()
            assert cache_dir.is_dir()

    def test_put_and_get(self):
        """Test storing and retrieving entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            entry = CacheEntry(
                key="test-key",
                response={"result": "ok"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="abc123",
                timestamp=time.time(),
                ttl=3600,
            )

            storage.put(entry)
            retrieved = storage.get("test-key")

            assert retrieved is not None
            assert retrieved.key == "test-key"
            assert retrieved.response == {"result": "ok"}

    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir))

            result = storage.get("nonexistent")
            assert result is None

    def test_get_expired_entry_returns_none(self):
        """Test that expired entries return None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            # Create entry that's already expired
            entry = CacheEntry(
                key="test-key",
                response={"result": "ok"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="abc123",
                timestamp=time.time() - 7200,  # 2 hours ago
                ttl=3600,  # 1 hour TTL (expired)
            )

            storage.put(entry)
            result = storage.get("test-key")

            assert result is None

    def test_delete(self):
        """Test deleting entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            entry = CacheEntry(
                key="test-key",
                response={"result": "ok"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="abc123",
                timestamp=time.time(),
            )

            storage.put(entry)
            assert storage.get("test-key") is not None

            deleted = storage.delete("test-key")
            assert deleted is True
            assert storage.get("test-key") is None

    def test_delete_nonexistent_returns_false(self):
        """Test deleting non-existent key returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir))

            result = storage.delete("nonexistent")
            assert result is False

    def test_clear(self):
        """Test clearing all entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            # Add multiple entries
            for i in range(3):
                entry = CacheEntry(
                    key=f"key-{i}",
                    response={"id": i},
                    workflow="code-review",
                    stage="scan",
                    model="sonnet",
                    prompt_hash=f"hash-{i}",
                    timestamp=time.time(),
                )
                storage.put(entry)

            # Clear all
            count = storage.clear()
            assert count == 3

            # All should be gone
            assert storage.get("key-0") is None
            assert storage.get("key-1") is None
            assert storage.get("key-2") is None

    def test_evict_expired(self):
        """Test evicting expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            current_time = time.time()

            # Add fresh entry
            fresh = CacheEntry(
                key="fresh",
                response={"status": "fresh"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="fresh-hash",
                timestamp=current_time,
                ttl=3600,
            )
            storage.put(fresh)

            # Add expired entry
            expired = CacheEntry(
                key="expired",
                response={"status": "expired"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="expired-hash",
                timestamp=current_time - 7200,  # 2 hours ago
                ttl=3600,  # 1 hour TTL
            )
            storage.put(expired)

            # Evict expired
            evicted_count = storage.evict_expired()
            assert evicted_count == 1

            # Fresh entry still there
            assert storage.get("fresh") is not None
            # Expired entry gone
            assert storage.get("expired") is None

    def test_get_all(self):
        """Test getting all non-expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            current_time = time.time()

            # Add fresh entries
            for i in range(3):
                entry = CacheEntry(
                    key=f"key-{i}",
                    response={"id": i},
                    workflow="code-review",
                    stage="scan",
                    model="sonnet",
                    prompt_hash=f"hash-{i}",
                    timestamp=current_time,
                    ttl=3600,
                )
                storage.put(entry)

            # Add expired entry
            expired = CacheEntry(
                key="expired",
                response={"id": 999},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="expired-hash",
                timestamp=current_time - 7200,
                ttl=3600,
            )
            storage.put(expired)

            # Get all (should exclude expired)
            all_entries = storage.get_all()
            assert len(all_entries) == 3
            assert all(e.key != "expired" for e in all_entries)

    def test_save_and_load(self):
        """Test saving to disk and loading on next init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Create storage and add entries
            storage1 = CacheStorage(cache_dir=cache_dir)

            entry = CacheEntry(
                key="persisted-key",
                response={"persisted": True},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="persist-hash",
                timestamp=time.time(),
                ttl=3600,
            )
            storage1.put(entry)

            # Create new storage instance (should load from disk)
            storage2 = CacheStorage(cache_dir=cache_dir)

            retrieved = storage2.get("persisted-key")
            assert retrieved is not None
            assert retrieved.response == {"persisted": True}

    def test_load_skips_expired_entries(self):
        """Test that loading from disk skips expired entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            cache_file = cache_dir / "responses.json"
            cache_dir.mkdir(exist_ok=True)

            # Manually create cache file with expired entry
            current_time = time.time()
            cache_data = {
                "version": "3.8.0",
                "timestamp": current_time,
                "entries": [
                    {
                        "key": "expired-key",
                        "response": {"status": "expired"},
                        "workflow": "code-review",
                        "stage": "scan",
                        "model": "sonnet",
                        "prompt_hash": "hash",
                        "timestamp": current_time - 7200,  # 2 hours ago
                        "ttl": 3600,  # 1 hour TTL
                    },
                ],
            }

            with open(cache_file, "w") as f:
                json.dump(cache_data, f)

            # Load storage (should skip expired)
            storage = CacheStorage(cache_dir=cache_dir)

            assert storage.get("expired-key") is None

    def test_size_mb(self):
        """Test cache size calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir))

            # Add entry and save
            entry = CacheEntry(
                key="test-key",
                response={"data": "x" * 1000},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="hash",
                timestamp=time.time(),
            )
            storage.put(entry)

            size = storage.size_mb()
            assert size > 0

    def test_stats(self):
        """Test storage statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = CacheStorage(cache_dir=Path(tmpdir), auto_save=False)

            current_time = time.time()

            # Add fresh entry
            fresh = CacheEntry(
                key="fresh",
                response={"status": "fresh"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="fresh-hash",
                timestamp=current_time,
                ttl=3600,
            )
            storage.put(fresh)

            # Add expired entry
            expired = CacheEntry(
                key="expired",
                response={"status": "expired"},
                workflow="code-review",
                stage="scan",
                model="sonnet",
                prompt_hash="expired-hash",
                timestamp=current_time - 7200,
                ttl=3600,
            )
            storage.put(expired)

            stats = storage.stats()
            assert stats["total_entries"] == 2
            assert stats["expired_entries"] == 1
            assert stats["active_entries"] == 1
            assert "cache_dir" in stats
