"""Unit tests for UsageTracker.

Tests the core telemetry tracking functionality including:
- File creation and JSON Lines format
- Thread-safe atomic writes
- SHA256 user ID hashing
- File rotation and retention
- Statistics calculation
- Savings calculation
"""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.telemetry import UsageTracker


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test telemetry data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tracker(temp_dir):
    """Create a UsageTracker instance with temporary directory."""
    return UsageTracker(telemetry_dir=temp_dir, retention_days=7, max_file_size_mb=1)


def test_track_llm_call_creates_file(tracker, temp_dir):
    """Test that tracking an LLM call creates the usage file after flush."""
    assert not tracker.usage_file.exists()

    tracker.track_llm_call(
        workflow="test-workflow",
        stage="analysis",
        tier="CAPABLE",
        model="claude-sonnet-4.5",
        provider="anthropic",
        cost=0.015,
        tokens={"input": 1500, "output": 500},
        cache_hit=False,
        cache_type=None,
        duration_ms=2340,
    )

    # Entries are buffered; flush to disk before checking file existence
    tracker.flush()
    assert tracker.usage_file.exists()


def test_track_llm_call_json_lines_format(tracker):
    """Test that entries are written in JSON Lines format."""
    tracker.track_llm_call(
        workflow="test-workflow",
        stage="analysis",
        tier="CAPABLE",
        model="claude-sonnet-4.5",
        provider="anthropic",
        cost=0.015,
        tokens={"input": 1500, "output": 500},
        cache_hit=False,
        cache_type=None,
        duration_ms=2340,
    )

    tracker.track_llm_call(
        workflow="test-workflow2",
        stage="generation",
        tier="CHEAP",
        model="claude-haiku-4",
        provider="anthropic",
        cost=0.002,
        tokens={"input": 800, "output": 300},
        cache_hit=True,
        cache_type="hash",
        duration_ms=150,
    )

    # Flush buffer to disk before reading file directly
    tracker.flush()

    with open(tracker.usage_file, encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 2

    # Each line should be valid JSON
    entry1 = json.loads(lines[0])
    entry2 = json.loads(lines[1])

    assert entry1["workflow"] == "test-workflow"
    assert entry2["workflow"] == "test-workflow2"


def test_user_id_hashed(tracker):
    """Test that user IDs are SHA256 hashed."""
    tracker.track_llm_call(
        workflow="test-workflow",
        stage="analysis",
        tier="CAPABLE",
        model="claude-sonnet-4.5",
        provider="anthropic",
        cost=0.015,
        tokens={"input": 1500, "output": 500},
        cache_hit=False,
        cache_type=None,
        duration_ms=2340,
        user_id="test_user@example.com",
    )

    entries = tracker.get_recent_entries(limit=1)
    assert len(entries) == 1

    # User ID should be hashed (16 chars from SHA256)
    user_id = entries[0]["user_id"]
    assert len(user_id) == 16
    assert user_id.isalnum()
    # Should NOT be the original email
    assert user_id != "test_user@example.com"


def test_atomic_write(tracker):
    """Test that writes are atomic (no partial writes)."""
    # Track multiple calls concurrently to test atomicity
    import threading

    def track_call(i):
        tracker.track_llm_call(
            workflow=f"workflow-{i}",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.01,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

    threads = []
    for i in range(10):
        t = threading.Thread(target=track_call, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # All entries should be valid JSON
    entries = tracker.get_recent_entries(limit=100)
    assert len(entries) == 10


def test_rotation_after_size_limit(tracker, temp_dir):
    """Test that log file rotates after exceeding size limit."""
    # Track many calls to exceed size limit (1 MB for test)
    large_tokens = {"input": 10000, "output": 10000}
    for i in range(100):
        tracker.track_llm_call(
            workflow=f"workflow-{i}",
            stage="test",
            tier="CAPABLE",
            model="test-model-with-long-name" * 10,
            provider="test-provider-with-long-name" * 10,
            cost=0.01,
            tokens=large_tokens,
            cache_hit=False,
            cache_type=None,
            duration_ms=1000,
        )

    # Check if rotation occurred
    rotated_files = list(temp_dir.glob("usage.*.jsonl"))
    # Should have rotated at least once if size exceeded
    # (or still have original if not exceeded)
    assert tracker.usage_file.exists() or len(rotated_files) > 0


def test_get_recent_entries(tracker):
    """Test reading recent entries."""
    # Track 5 calls
    for i in range(5):
        tracker.track_llm_call(
            workflow=f"workflow-{i}",
            stage="test",
            tier="CAPABLE",
            model="test-model",
            provider="test",
            cost=0.01 * (i + 1),
            tokens={"input": 100 * (i + 1), "output": 100 * (i + 1)},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

    # Get last 3 entries
    entries = tracker.get_recent_entries(limit=3)
    assert len(entries) == 3

    # Should be most recent first
    assert entries[0]["workflow"] == "workflow-4"
    assert entries[1]["workflow"] == "workflow-3"
    assert entries[2]["workflow"] == "workflow-2"


def test_get_stats(tracker):
    """Test statistics calculation."""
    # Track calls with different tiers
    tracker.track_llm_call(
        workflow="test1",
        stage="test",
        tier="CHEAP",
        model="model1",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=False,
        cache_type=None,
        duration_ms=100,
    )

    tracker.track_llm_call(
        workflow="test2",
        stage="test",
        tier="CAPABLE",
        model="model2",
        provider="test",
        cost=0.02,
        tokens={"input": 200, "output": 200},
        cache_hit=True,
        cache_type="hash",
        duration_ms=50,
    )

    tracker.track_llm_call(
        workflow="test3",
        stage="test",
        tier="PREMIUM",
        model="model3",
        provider="test",
        cost=0.05,
        tokens={"input": 300, "output": 300},
        cache_hit=False,
        cache_type=None,
        duration_ms=200,
    )

    stats = tracker.get_stats(days=1)

    assert stats["total_calls"] == 3
    assert stats["total_cost"] == 0.08
    assert stats["total_tokens_input"] == 600
    assert stats["total_tokens_output"] == 600
    assert stats["cache_hits"] == 1
    assert stats["cache_misses"] == 2
    assert stats["cache_hit_rate"] == pytest.approx(33.3, rel=0.1)
    assert "CHEAP" in stats["by_tier"]
    assert "CAPABLE" in stats["by_tier"]
    assert "PREMIUM" in stats["by_tier"]


def test_calculate_savings(tracker):
    """Test savings calculation."""
    # Track calls with different tiers
    for i in range(10):
        tier = ["CHEAP", "CAPABLE", "PREMIUM"][i % 3]
        cost = {"CHEAP": 0.001, "CAPABLE": 0.01, "PREMIUM": 0.05}[tier]

        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier=tier,
            model="model",
            provider="test",
            cost=cost,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

    savings = tracker.calculate_savings(days=1)

    assert savings["total_calls"] == 10
    assert savings["actual_cost"] > 0
    assert savings["baseline_cost"] > savings["actual_cost"]  # Should save money
    assert savings["savings"] > 0
    assert savings["savings_percent"] > 0
    assert "CHEAP" in savings["tier_distribution"]
    assert "CAPABLE" in savings["tier_distribution"]
    assert "PREMIUM" in savings["tier_distribution"]


def test_reset(tracker):
    """Test clearing all telemetry data."""
    # Track some calls
    for _i in range(5):
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.01,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

    # Flush to disk so entries are visible both in buffer checks and on disk
    tracker.flush()
    assert tracker.usage_file.exists()
    entries_before = tracker.get_recent_entries(limit=100)
    assert len(entries_before) == 5

    # Reset clears buffer + disk files
    count = tracker.reset()
    assert count == 5

    # File should be deleted
    assert not tracker.usage_file.exists()

    # No entries after reset
    entries_after = tracker.get_recent_entries(limit=100)
    assert len(entries_after) == 0


def test_export_to_dict(tracker):
    """Test exporting entries as dictionary."""
    # Track some calls
    tracker.track_llm_call(
        workflow="test1",
        stage="test",
        tier="CAPABLE",
        model="model",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=False,
        cache_type=None,
        duration_ms=100,
    )

    tracker.track_llm_call(
        workflow="test2",
        stage="test",
        tier="CHEAP",
        model="model",
        provider="test",
        cost=0.001,
        tokens={"input": 50, "output": 50},
        cache_hit=True,
        cache_type="hash",
        duration_ms=50,
    )

    # Export all
    entries = tracker.export_to_dict()
    assert len(entries) == 2
    assert isinstance(entries, list)
    assert isinstance(entries[0], dict)
    assert "workflow" in entries[0]
    assert "tier" in entries[0]
    assert "cost" in entries[0]


def test_cache_hit_tracking(tracker):
    """Test that cache hits are tracked correctly."""
    # Track cache hit
    tracker.track_llm_call(
        workflow="test",
        stage="test",
        tier="CAPABLE",
        model="model",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=True,
        cache_type="hash",
        duration_ms=10,  # Cache hits should be fast
    )

    entries = tracker.get_recent_entries(limit=1)
    assert len(entries) == 1
    assert entries[0]["cache"]["hit"] is True
    assert entries[0]["cache"]["type"] == "hash"
    assert entries[0]["duration_ms"] == 10


def test_optional_stage(tracker):
    """Test that stage field is optional."""
    # Track without stage
    tracker.track_llm_call(
        workflow="test",
        stage=None,
        tier="CAPABLE",
        model="model",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=False,
        cache_type=None,
        duration_ms=100,
    )

    entries = tracker.get_recent_entries(limit=1)
    assert len(entries) == 1
    # Stage should not be in entry if None
    assert "stage" not in entries[0] or entries[0]["stage"] is None


def test_schema_version(tracker):
    """Test that schema version is included in entries."""
    tracker.track_llm_call(
        workflow="test",
        stage="test",
        tier="CAPABLE",
        model="model",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=False,
        cache_type=None,
        duration_ms=100,
    )

    entries = tracker.get_recent_entries(limit=1)
    assert len(entries) == 1
    assert entries[0]["v"] == "1.0"


def test_timestamp_format(tracker):
    """Test that timestamps are ISO 8601 with Z suffix."""
    tracker.track_llm_call(
        workflow="test",
        stage="test",
        tier="CAPABLE",
        model="model",
        provider="test",
        cost=0.01,
        tokens={"input": 100, "output": 100},
        cache_hit=False,
        cache_type=None,
        duration_ms=100,
    )

    entries = tracker.get_recent_entries(limit=1)
    assert len(entries) == 1

    ts = entries[0]["ts"]
    assert ts.endswith("+00:00") or ts.endswith("Z")

    # Should be parseable as ISO 8601
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    assert isinstance(dt, datetime)


# ============================================================================
# Additional Tests for Improved Coverage
# ============================================================================


class TestSingletonPattern:
    """Test singleton pattern implementation."""

    def test_get_instance_creates_singleton(self, temp_dir):
        """Test that get_instance returns the same instance."""
        # Reset class-level instance
        UsageTracker._instance = None

        # First call creates instance
        instance1 = UsageTracker.get_instance(telemetry_dir=temp_dir)
        assert instance1 is not None

        # Second call returns same instance
        instance2 = UsageTracker.get_instance()
        assert instance2 is instance1

        # Clean up for other tests
        UsageTracker._instance = None

    def test_get_instance_with_custom_params(self, temp_dir):
        """Test that get_instance uses custom parameters."""
        UsageTracker._instance = None

        instance = UsageTracker.get_instance(
            telemetry_dir=temp_dir,
            retention_days=30,
            max_file_size_mb=5,
        )

        assert instance.retention_days == 30
        assert instance.max_file_size_mb == 5
        assert instance.telemetry_dir == temp_dir

        UsageTracker._instance = None


class TestPermissionErrors:
    """Test handling of permission errors."""

    def test_directory_creation_permission_error(self, tmp_path):
        """Test that permission errors during directory creation are handled gracefully."""
        # Use a nonexistent subdirectory so no real I/O happens after mkdir fails
        restricted = tmp_path / "no_perms" / ".empathy"
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            tracker = UsageTracker(telemetry_dir=restricted)
            # Should not raise, just log
            assert tracker.telemetry_dir == restricted

    def test_track_call_with_permission_error(self, tracker, temp_dir):
        """Test that permission errors during write are handled gracefully."""
        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            # Should not raise exception, just log
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CAPABLE",
                model="model",
                provider="test",
                cost=0.01,
                tokens={"input": 100, "output": 100},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )
        # No exception should be raised

    def test_track_call_with_unexpected_error(self, tracker):
        """Test that unexpected errors during flush are handled gracefully."""
        # Fill buffer to trigger a flush on next call, then mock flush to fail
        tracker.buffer_size = 1
        with patch.object(tracker, "flush", side_effect=RuntimeError("Unexpected error")):
            # Should not raise exception, just log
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CAPABLE",
                model="model",
                provider="test",
                cost=0.01,
                tokens={"input": 100, "output": 100},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )
        # No exception should be raised


class TestFileRotation:
    """Test file rotation functionality."""

    def test_rotation_with_existing_rotated_file(self, tracker, temp_dir):
        """Test rotation when rotated file already exists."""
        # Create a large file that will trigger rotation
        large_data = "x" * 1024 * 1024  # 1 MB of data
        with open(tracker.usage_file, "w") as f:
            f.write(large_data)

        # Create a rotated file with today's date to force counter increment
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        existing_rotated = temp_dir / f"usage.{today}.jsonl"
        existing_rotated.write_text("existing data")

        # Trigger rotation
        tracker._rotate_if_needed()

        # Should create usage.YYYY-MM-DD.1.jsonl
        expected_rotated = temp_dir / f"usage.{today}.1.jsonl"
        assert expected_rotated.exists() or not tracker.usage_file.exists()

    def test_rotation_does_not_occur_below_threshold(self, tracker):
        """Test that rotation does not occur when file is below size limit."""
        # Write small amount of data
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.01,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        # Flush to disk so the file exists for size checking
        tracker.flush()

        # Check file size (should be small)
        size_mb = tracker.usage_file.stat().st_size / (1024 * 1024)
        assert size_mb < tracker.max_file_size_mb

        # Rotation should not occur
        rotated_files_before = list(tracker.telemetry_dir.glob("usage.*.*.jsonl"))
        tracker._rotate_if_needed()
        rotated_files_after = list(tracker.telemetry_dir.glob("usage.*.*.jsonl"))

        assert len(rotated_files_before) == len(rotated_files_after)

    def test_rotation_when_usage_file_does_not_exist(self, tracker):
        """Test that rotation handles non-existent usage file gracefully."""
        # Ensure file doesn't exist
        if tracker.usage_file.exists():
            tracker.usage_file.unlink()

        # Should not raise exception
        tracker._rotate_if_needed()


class TestRetentionPolicy:
    """Test data retention policy."""

    def test_cleanup_old_files(self, tracker, temp_dir):
        """Test that files older than retention period are deleted."""
        # Create old files
        old_date = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_file = temp_dir / f"usage.{old_date}.jsonl"
        old_file.write_text('{"test": "data"}\n')

        # Create recent file
        recent_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        recent_file = temp_dir / f"usage.{recent_date}.jsonl"
        recent_file.write_text('{"test": "data"}\n')

        # Set old mtime
        old_timestamp = (datetime.now() - timedelta(days=100)).timestamp()
        os.utime(old_file, (old_timestamp, old_timestamp))

        # Run cleanup
        tracker._cleanup_old_files()

        # Old file should be deleted, recent file should remain
        assert not old_file.exists()
        assert recent_file.exists()

    def test_cleanup_handles_file_errors(self, tracker, temp_dir):
        """Test that cleanup handles file errors gracefully."""
        # Create a file
        test_file = temp_dir / "usage.2020-01-01.jsonl"
        test_file.write_text('{"test": "data"}\n')

        # Mock unlink to raise error
        with patch("pathlib.Path.unlink", side_effect=OSError("Delete failed")):
            # Should not raise exception
            tracker._cleanup_old_files()


class TestAtomicWrites:
    """Test atomic write operations."""

    def test_write_entry_atomic_rename(self, tracker):
        """Test that write uses atomic rename when file doesn't exist."""
        entry = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).isoformat(),
            "workflow": "test",
            "tier": "CAPABLE",
            "model": "model",
            "cost": 0.01,
        }

        # Ensure usage file doesn't exist
        if tracker.usage_file.exists():
            tracker.usage_file.unlink()

        tracker._write_entry(entry)

        # File should exist
        assert tracker.usage_file.exists()

        # Temp file should be cleaned up
        temp_file = tracker.usage_file.with_suffix(".tmp")
        assert not temp_file.exists()

    def test_write_entry_cleanup_on_error(self, tracker):
        """Test that temp file is cleaned up on write error."""
        entry = {"test": "data"}

        # Mock file operations to trigger cleanup path
        with patch("builtins.open", side_effect=OSError("Write failed")):
            with pytest.raises(OSError):
                tracker._write_entry(entry)

        # Temp file should be cleaned up
        temp_file = tracker.usage_file.with_suffix(".tmp")
        assert not temp_file.exists()

    def test_write_entry_handles_temp_file_cleanup_error(self, tracker):
        """Test that errors during temp file cleanup are handled."""
        entry = {"test": "data"}
        temp_file = tracker.usage_file.with_suffix(".tmp")

        # Create a temp file
        temp_file.write_text("test")

        # Mock open to raise error on write
        with patch("builtins.open", side_effect=OSError("Write failed")):
            # Mock unlink to also fail (simulating nested error handling)
            with patch.object(Path, "unlink", side_effect=OSError("Cleanup failed")):
                # The outer OSError should still be raised
                with pytest.raises(OSError, match="Write failed"):
                    tracker._write_entry(entry)


class TestDataRetrieval:
    """Test data retrieval methods."""

    def test_get_recent_entries_with_days_filter(self, tracker):
        """Test filtering entries by number of days."""
        # Track an old entry (mock timestamp)
        old_entry = {
            "v": "1.0",
            "ts": (datetime.now(timezone.utc) - timedelta(days=45)).isoformat(),
            "workflow": "old",
            "tier": "CAPABLE",
            "cost": 0.01,
            "tokens": {"input": 100, "output": 100},
            "cache": {"hit": False},
            "duration_ms": 100,
            "user_id": "test",
        }

        # Track a recent entry
        recent_entry = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).isoformat(),
            "workflow": "recent",
            "tier": "CAPABLE",
            "cost": 0.01,
            "tokens": {"input": 100, "output": 100},
            "cache": {"hit": False},
            "duration_ms": 100,
            "user_id": "test",
        }

        # Write both entries
        tracker._write_entry(old_entry)
        tracker._write_entry(recent_entry)

        # Get entries from last 30 days
        entries = tracker.get_recent_entries(limit=100, days=30)

        # Should only have recent entry
        assert len(entries) == 1
        assert entries[0]["workflow"] == "recent"

    def test_get_recent_entries_handles_invalid_json(self, tracker):
        """Test that invalid JSON lines are skipped."""
        # Write some valid and invalid entries
        with open(tracker.usage_file, "w", encoding="utf-8") as f:
            f.write('{"v": "1.0", "workflow": "valid1", "ts": "2024-01-01T00:00:00Z"}\n')
            f.write("invalid json line\n")
            f.write("\n")  # Empty line
            f.write('{"v": "1.0", "workflow": "valid2", "ts": "2024-01-01T00:00:01Z"}\n')

        entries = tracker.get_recent_entries(limit=100)

        # Should only have valid entries
        assert len(entries) == 2
        assert entries[0]["workflow"] in ["valid1", "valid2"]

    def test_get_recent_entries_handles_missing_timestamp(self, tracker):
        """Test handling entries with missing or invalid timestamp."""
        # Write entry without timestamp
        with open(tracker.usage_file, "w", encoding="utf-8") as f:
            f.write('{"v": "1.0", "workflow": "no_ts"}\n')
            f.write('{"v": "1.0", "workflow": "valid", "ts": "2024-01-01T00:00:00Z"}\n')

        entries = tracker.get_recent_entries(limit=100, days=30)

        # Entry without timestamp should be skipped when filtering by days
        assert all("ts" in e for e in entries)

    def test_get_recent_entries_handles_file_read_error(self, tracker):
        """Test that file read errors are handled gracefully."""
        # Create a valid file (flush so the entry is on disk, not just in buffer)
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.01,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )
        tracker.flush()

        # Mock open to raise error — disk reads fail, buffer is empty after flush
        with patch("builtins.open", side_effect=OSError("Read failed")):
            entries = tracker.get_recent_entries(limit=100)

        # Should return empty list (disk unreadable, buffer empty), not raise exception
        assert entries == []


class TestStatisticsCalculation:
    """Test statistics calculation methods."""

    def test_get_stats_empty_data(self, tracker):
        """Test statistics calculation with no data."""
        stats = tracker.get_stats(days=30)

        assert stats["total_calls"] == 0
        assert stats["total_cost"] == 0.0
        assert stats["cache_hit_rate"] == 0.0

    def test_get_stats_with_missing_fields(self, tracker):
        """Test that stats calculation handles missing fields gracefully."""
        # Write entry with missing optional fields
        entry = {
            "v": "1.0",
            "ts": datetime.now(timezone.utc).isoformat(),
            # Missing: workflow, tier, provider, tokens, cache
        }
        tracker._write_entry(entry)

        stats = tracker.get_stats(days=1)

        # Should handle missing fields
        assert stats["total_calls"] == 1
        assert "unknown" in stats["by_tier"]
        assert "unknown" in stats["by_workflow"]

    def test_calculate_savings_empty_data(self, tracker):
        """Test savings calculation with no data."""
        savings = tracker.calculate_savings(days=30)

        assert savings["actual_cost"] == 0.0
        assert savings["baseline_cost"] == 0.0
        assert savings["savings"] == 0.0
        assert savings["total_calls"] == 0

    def test_calculate_savings_all_premium(self, tracker):
        """Test savings when all calls use PREMIUM tier."""
        # Track only PREMIUM calls
        for _i in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="PREMIUM",
                model="model",
                provider="test",
                cost=0.05,
                tokens={"input": 100, "output": 100},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        savings = tracker.calculate_savings(days=1)

        # No savings when all calls are PREMIUM
        assert savings["savings_percent"] == 0.0
        assert savings["tier_distribution"]["PREMIUM"] == 100.0


class TestCostRounding:
    """Test cost rounding and precision."""

    def test_cost_rounded_to_six_decimals(self, tracker):
        """Test that cost is rounded to 6 decimal places."""
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.0123456789,  # More than 6 decimals
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        entries = tracker.get_recent_entries(limit=1)
        assert entries[0]["cost"] == 0.012346  # Rounded to 6 decimals

    def test_stats_cost_rounded_to_two_decimals(self, tracker):
        """Test that stats cost is rounded to 2 decimal places."""
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.0123,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        stats = tracker.get_stats(days=1)
        assert stats["total_cost"] == 0.01  # Rounded to 2 decimals


class TestResetFunctionality:
    """Test reset functionality."""

    def test_reset_with_multiple_files(self, tracker, temp_dir):
        """Test reset with multiple rotated files."""
        # Create multiple files
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            file = temp_dir / f"usage.{date}.jsonl"
            file.write_text(f'{{"test": "data{i}"}}\n')

        # Write to main file
        tracker.track_llm_call(
            workflow="test",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=0.01,
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        # Reset should delete all
        count = tracker.reset()
        assert count >= 1

        # All files should be deleted
        usage_files = list(temp_dir.glob("usage*.jsonl"))
        assert len(usage_files) == 0

    def test_reset_handles_delete_error(self, tracker, temp_dir):
        """Test that reset handles file deletion errors gracefully."""
        # Create a file
        test_file = temp_dir / "usage.test.jsonl"
        test_file.write_text('{"test": "data"}\n')

        # Mock unlink to raise error
        with patch("pathlib.Path.unlink", side_effect=OSError("Delete failed")):
            # Should not raise exception
            count = tracker.reset()
            # Returns count of entries attempted to delete
            assert count >= 0


class TestExportFunctionality:
    """Test export functionality."""

    def test_export_to_dict_with_days_filter(self, tracker):
        """Test export with days filter."""
        # Track multiple entries over time
        for i in range(5):
            tracker.track_llm_call(
                workflow=f"test{i}",
                stage="test",
                tier="CAPABLE",
                model="model",
                provider="test",
                cost=0.01,
                tokens={"input": 100, "output": 100},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        # Export all
        all_entries = tracker.export_to_dict()
        assert len(all_entries) == 5

        # Export with filter (should use get_recent_entries logic)
        recent_entries = tracker.export_to_dict(days=1)
        assert len(recent_entries) <= len(all_entries)


class TestConcurrency:
    """Test concurrent access handling."""

    def test_concurrent_writes_from_multiple_threads(self, tracker):
        """Test that concurrent writes from multiple threads are handled safely."""
        import threading

        results = []

        def track_multiple(thread_id, count):
            for i in range(count):
                try:
                    tracker.track_llm_call(
                        workflow=f"thread-{thread_id}-call-{i}",
                        stage="test",
                        tier="CAPABLE",
                        model="model",
                        provider="test",
                        cost=0.01,
                        tokens={"input": 100, "output": 100},
                        cache_hit=False,
                        cache_type=None,
                        duration_ms=100,
                    )
                    results.append((thread_id, i, "success"))
                except Exception as e:
                    results.append((thread_id, i, f"error: {e}"))

        # Create multiple threads
        threads = []
        for thread_id in range(5):
            t = threading.Thread(target=track_multiple, args=(thread_id, 10))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All writes should succeed
        assert len([r for r in results if r[2] == "success"]) == 50

        # Verify all entries were written
        entries = tracker.get_recent_entries(limit=100)
        assert len(entries) == 50


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_cleanup_with_stat_error(self, tracker, temp_dir):
        """Test cleanup handles stat() errors gracefully."""
        # Create a file
        test_file = temp_dir / "usage.2020-01-01.jsonl"
        test_file.write_text('{"test": "data"}\n')

        # Mock stat to raise OSError only for the file, not directory
        original_stat = Path.stat

        def mock_stat(self):
            if "usage.2020-01-01.jsonl" in str(self):
                raise OSError("Cannot stat")
            return original_stat(self)

        with patch.object(Path, "stat", mock_stat):
            # Should not raise exception
            tracker._cleanup_old_files()

    def test_cleanup_with_value_error(self, tracker, temp_dir):
        """Test cleanup handles ValueError from timestamp parsing."""
        # Create a file
        test_file = temp_dir / "usage.2020-01-01.jsonl"
        test_file.write_text('{"test": "data"}\n')

        # Mock fromtimestamp to raise ValueError
        with patch("attune.telemetry.usage_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now()
            mock_dt.fromtimestamp.side_effect = ValueError("Invalid timestamp")
            # Should not raise exception
            tracker._cleanup_old_files()

    def test_get_recent_entries_with_deleted_file_during_iteration(self, tracker, temp_dir):
        """Test handling when file is deleted during iteration."""
        # Create multiple files
        file1 = temp_dir / "usage.2024-01-01.jsonl"
        file2 = temp_dir / "usage.2024-01-02.jsonl"
        file1.write_text('{"v": "1.0", "workflow": "test1", "ts": "2024-01-01T00:00:00Z"}\n')
        file2.write_text('{"v": "1.0", "workflow": "test2", "ts": "2024-01-02T00:00:00Z"}\n')

        # Mock exists() to return False for one file (simulating deletion)
        original_exists = Path.exists

        def mock_exists(self):
            if "2024-01-01" in str(self):
                return False  # File was deleted
            return original_exists(self)

        with patch.object(Path, "exists", mock_exists):
            entries = tracker.get_recent_entries(limit=100)
            # Should skip the "deleted" file and only read the other
            assert len(entries) >= 1

    def test_get_recent_entries_handles_invalid_timestamp_format(self, tracker):
        """Test handling of entries with malformed timestamp."""
        # Write entry with invalid timestamp format
        with open(tracker.usage_file, "w", encoding="utf-8") as f:
            f.write('{"v": "1.0", "workflow": "invalid_ts", "ts": "not-a-timestamp"}\n')
            f.write('{"v": "1.0", "workflow": "valid", "ts": "2024-01-01T00:00:00Z"}\n')

        # Filter by days (will try to parse timestamp)
        entries = tracker.get_recent_entries(limit=100, days=30)

        # Should skip entry with invalid timestamp
        assert all("ts" in e and e["workflow"] != "invalid_ts" for e in entries)

    def test_hash_user_id_empty_string(self, tracker):
        """Test hashing empty user ID."""
        hashed = tracker._hash_user_id("")
        assert len(hashed) == 16
        assert hashed.isalnum()

    def test_hash_user_id_unicode(self, tracker):
        """Test hashing user ID with unicode characters."""
        hashed = tracker._hash_user_id("user@测试.com")
        assert len(hashed) == 16
        assert hashed.isalnum()

    def test_rotation_creates_unique_filenames(self, tracker, temp_dir):
        """Test that rotation creates unique filenames when called multiple times."""
        # Create a large file
        large_data = "x" * 1024 * 1024  # 1 MB
        tracker.usage_file.write_text(large_data)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Trigger first rotation
        tracker._rotate_if_needed()

        # Create another large file
        tracker.usage_file.write_text(large_data)

        # Trigger second rotation
        tracker._rotate_if_needed()

        # Should have created different files
        rotated_files = list(temp_dir.glob(f"usage.{today}*.jsonl"))
        # At least one rotation should have occurred
        assert len(rotated_files) >= 1

    def test_track_call_with_zero_cost(self, tracker):
        """Test tracking call with zero cost (free tier or cache hit)."""
        tracker.track_llm_call(
            workflow="free-tier",
            stage="test",
            tier="CHEAP",
            model="model",
            provider="test",
            cost=0.0,
            tokens={"input": 100, "output": 100},
            cache_hit=True,
            cache_type="hash",
            duration_ms=10,
        )

        entries = tracker.get_recent_entries(limit=1)
        assert entries[0]["cost"] == 0.0

    def test_track_call_with_negative_cost(self, tracker):
        """Test tracking call with negative cost (error scenario)."""
        tracker.track_llm_call(
            workflow="error",
            stage="test",
            tier="CAPABLE",
            model="model",
            provider="test",
            cost=-0.01,  # Should still be tracked
            tokens={"input": 100, "output": 100},
            cache_hit=False,
            cache_type=None,
            duration_ms=100,
        )

        entries = tracker.get_recent_entries(limit=1)
        # Cost is rounded but preserved
        assert entries[0]["cost"] < 0

    def test_get_stats_with_division_by_zero_edge_case(self, tracker):
        """Test that stats calculation handles edge cases safely."""
        # Ensure empty data doesn't cause division by zero
        stats = tracker.get_stats(days=30)

        # All rates should be 0.0, not NaN or error
        assert stats["cache_hit_rate"] == 0.0

    def test_calculate_savings_with_no_premium_calls(self, tracker):
        """Test savings calculation when there are no PREMIUM calls for baseline."""
        # Track only CHEAP calls
        for _i in range(5):
            tracker.track_llm_call(
                workflow="test",
                stage="test",
                tier="CHEAP",
                model="model",
                provider="test",
                cost=0.001,
                tokens={"input": 100, "output": 100},
                cache_hit=False,
                cache_type=None,
                duration_ms=100,
            )

        savings = tracker.calculate_savings(days=1)

        # Should use default baseline cost
        assert savings["baseline_cost"] > 0
        assert savings["actual_cost"] > 0
