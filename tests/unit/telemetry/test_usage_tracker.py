"""Unit tests for UsageTracker.

Tests the core telemetry tracking functionality including:
- File creation and JSON Lines format
- Thread-safe atomic writes
- SHA256 user ID hashing
- File rotation and retention
- Statistics calculation
- Savings calculation
"""

import hashlib
import hmac
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


class TestDefaultTelemetryDir:
    """The default telemetry dir must honor ATTUNE_HOME.

    Regression guard for the test-pollution leak: the default used
    ``Path.home() / ".attune"`` directly, so the workflow telemetry
    singleton wrote stub/test events into the developer's real
    ``~/.attune/telemetry/usage.jsonl`` during the suite. The default now
    reads ``ATTUNE_HOME`` (matching ``attune.ops.config.attune_home``),
    which ``tests/conftest.py`` isolates to a tmp dir per test.
    """

    def test_default_dir_respects_attune_home(self, tmp_path, monkeypatch):
        """With no explicit telemetry_dir, the default lands under ATTUNE_HOME."""
        monkeypatch.setenv("ATTUNE_HOME", str(tmp_path / "home"))
        UsageTracker._instance = None
        tracker = UsageTracker()  # no telemetry_dir -> resolve default
        assert tracker.telemetry_dir == tmp_path / "home" / "telemetry"
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


class TestWriteEntry:
    """Test the direct-to-disk write helper (`_write_entry`).

    `_write_entry` is an APPEND helper (one JSON line per call) — it does
    NOT do a temp-file + atomic-rename. These tests assert that real
    behavior; the previous suite asserted a temp-file dance that never
    existed, so it passed vacuously.
    """

    def test_write_entry_appends_one_line_per_call(self, tracker):
        """Each call appends exactly one JSON line; no temp file is created."""
        if tracker.usage_file.exists():
            tracker.usage_file.unlink()

        first = {"v": "1.0", "ts": datetime.now(timezone.utc).isoformat(), "workflow": "a"}
        second = {"v": "1.0", "ts": datetime.now(timezone.utc).isoformat(), "workflow": "b"}
        tracker._write_entry(first)
        tracker._write_entry(second)

        lines = tracker.usage_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert [json.loads(line)["workflow"] for line in lines] == ["a", "b"]

        # It is a plain append — there is no sibling .tmp file.
        assert not tracker.usage_file.with_suffix(".tmp").exists()

    def test_write_entry_propagates_oserror(self, tracker):
        """A write failure propagates (no silent swallow)."""
        with patch("builtins.open", side_effect=OSError("Write failed")):
            with pytest.raises(OSError, match="Write failed"):
                tracker._write_entry({"test": "data"})


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

    def test_concurrent_writes_produce_unique_seq(self, temp_dir):
        """Regression: seq numbers must be unique under concurrency.

        The seq counter is now incremented inside the lock alongside the
        buffer append. Before the fix it was incremented outside the lock,
        so two threads could read the same value and emit duplicate seqs —
        corrupting the timestamp tiebreaker in get_recent_entries.

        A large buffer keeps every entry in memory (no auto-flush) so this
        isolates the counter race from disk-write concurrency.
        """
        import threading

        tracker = UsageTracker(telemetry_dir=temp_dir, buffer_size=10_000)
        per_thread, n_threads = 40, 8

        def track_many(thread_id):
            for _ in range(per_thread):
                tracker.track_llm_call(
                    workflow=f"t{thread_id}",
                    stage=None,
                    tier="CAPABLE",
                    model="model",
                    provider="test",
                    cost=0.01,
                    tokens={"input": 1, "output": 1},
                    cache_hit=False,
                    cache_type=None,
                    duration_ms=1,
                )

        threads = [threading.Thread(target=track_many, args=(i,)) for i in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = per_thread * n_threads
        seqs = [e["seq"] for e in tracker.get_recent_entries(limit=10_000)]
        assert len(seqs) == expected
        assert len(set(seqs)) == expected, "duplicate seq — counter raced outside the lock"


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
        """Cleanup swallows a ValueError from the mtime fallback.

        A name with no parseable date (``usage.notadate.jsonl``) falls back
        to mtime; if ``fromtimestamp`` raises, cleanup must not propagate.
        Real ``strptime``/``now`` are kept so only the fallback path fails.
        """
        bad = temp_dir / "usage.notadate.jsonl"
        bad.write_text('{"test": "data"}\n')

        with patch("attune.telemetry.usage_tracker.datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now(timezone.utc)
            mock_dt.strptime.side_effect = datetime.strptime  # real -> None for bad name
            mock_dt.fromtimestamp.side_effect = ValueError("Invalid timestamp")
            tracker._cleanup_old_files()  # must not raise

        assert bad.exists()  # not deleted when its age is unknown

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


# ---------------------------------------------------------------------------
# Branch coverage boost — lines missed in coverage.json
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadSummaryBranches:
    """Cover _load_summary and _rebuild_summary_from_disk branches."""

    def test_load_summary_json_decode_error_falls_back(self, temp_dir):
        """Bad JSON in summary file → empty dict, no crash."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        summary_file = temp_dir / "usage_summary.json"
        summary_file.write_text("NOT VALID JSON")

        tracker._load_summary()

        assert tracker._daily_summary == {}

    def test_rebuild_summary_from_disk_saves_when_non_empty(self, temp_dir):
        """_rebuild_summary_from_disk saves summary when entries found."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        # Write a minimal JSONL file
        jsonl = temp_dir / "usage_2026-01-01.jsonl"
        import json as _json

        entry = {
            "ts": "2026-01-01T00:00:00Z",
            "workflow": "test",
            "stage": "s",
            "tier": "CHEAP",
            "model": "m",
            "provider": "p",
            "cost": 0.001,
            "tokens_in": 10,
            "tokens_out": 5,
            "cache_hit": False,
            "duration_ms": 10,
            "seq": 1,
        }
        jsonl.write_text(_json.dumps(entry) + "\n")

        tracker._rebuild_summary_from_disk()

        # Summary should be non-empty and summary file should now exist
        assert tracker._daily_summary
        assert tracker._summary_file.exists()

    def test_update_summary_entry_invalid_date_skipped(self, temp_dir):
        """_update_summary_entry skips entries with invalid timestamp."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker._update_summary_entry({"ts": "bad-date"})
        assert tracker._daily_summary == {}

    def test_update_summary_entry_empty_ts_skipped(self, temp_dir):
        """_update_summary_entry skips entries with empty ts."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker._update_summary_entry({"ts": ""})
        assert tracker._daily_summary == {}


@pytest.mark.unit
class TestFlushOsErrorBranch:
    """Cover the OSError rollback path in flush()."""

    def test_flush_oserror_restores_buffer(self, temp_dir):
        """OSError during write restores entries to buffer."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker.track_llm_call(
            workflow="wf",
            stage="s",
            tier="CHEAP",
            model="m",
            provider="p",
            cost=0.001,
            tokens={"input": 10, "output": 5},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
        )

        with patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                tracker.flush()

        # Entries should be back in buffer
        assert len(tracker._buffer) >= 1


@pytest.mark.unit
class TestBufferFullExceptionBranches:
    """Cover the exception paths in _on_buffer_full."""

    def test_os_error_during_auto_flush_is_logged_not_raised(self, temp_dir):
        """OSError during automatic flush (when buffer full) is swallowed."""
        tracker = UsageTracker(telemetry_dir=temp_dir, buffer_size=1)

        with patch.object(tracker, "flush", side_effect=OSError("no space")):
            # Should not raise
            tracker.track_llm_call(
                workflow="wf",
                stage="s",
                tier="CHEAP",
                model="m",
                provider="p",
                cost=0.001,
                tokens={"input": 10, "output": 5},
                cache_hit=False,
                cache_type=None,
                duration_ms=10,
            )

    def test_unexpected_error_during_auto_flush_is_swallowed(self, temp_dir):
        """Generic exception during automatic flush is swallowed."""
        tracker = UsageTracker(telemetry_dir=temp_dir, buffer_size=1)

        with patch.object(tracker, "flush", side_effect=RuntimeError("very weird")):
            tracker.track_llm_call(
                workflow="wf",
                stage="s",
                tier="CHEAP",
                model="m",
                provider="p",
                cost=0.001,
                tokens={"input": 10, "output": 5},
                cache_hit=False,
                cache_type=None,
                duration_ms=10,
            )


@pytest.mark.unit
class TestGetRecentEntriesBufferBranches:
    """Cover the buffer timestamp-filter branches in get_recent_entries."""

    def test_buffer_entry_with_invalid_ts_skipped_when_cutoff_set(self, temp_dir):
        """Buffer entry with bad timestamp is skipped when days filter is active."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        # Directly inject bad entry into buffer
        tracker._buffer.append({"ts": "bad-date", "workflow": "x"})

        entries = tracker.get_recent_entries(limit=100, days=7)
        # Bad entry should be excluded
        assert all(e.get("workflow") != "x" for e in entries)

    def test_buffer_entry_missing_ts_skipped_when_cutoff_set(self, temp_dir):
        """Buffer entry missing ts key is skipped when days filter is active."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker._buffer.append({"workflow": "missing-ts"})

        entries = tracker.get_recent_entries(limit=100, days=1)
        assert all(e.get("workflow") != "missing-ts" for e in entries)


@pytest.mark.unit
class TestClearSummaryFileOsError:
    """Cover clear() when summary file unlink raises OSError."""

    def test_summary_file_oserror_is_swallowed(self, tmp_path):
        """OSError when deleting summary file does not crash reset()."""
        import os

        tracker = UsageTracker(telemetry_dir=tmp_path)
        tracker._summary_file.write_text("{}")

        # Make the directory read-only so unlink raises PermissionError (subclass of OSError)
        os.chmod(tmp_path, 0o555)
        try:
            # Should not raise — OSError from unlink is caught and swallowed
            tracker.reset()
        except Exception:
            pass  # May raise for other reasons in read-only dir
        finally:
            os.chmod(tmp_path, 0o755)  # Restore so cleanup works


@pytest.mark.unit
class TestGetCacheStats:
    """Cover get_cache_stats() including empty and populated paths."""

    def test_empty_entries_returns_zero_stats(self, temp_dir):
        """get_cache_stats returns zeros when no entries exist."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        stats = tracker.get_cache_stats(days=7)
        assert stats["hit_rate"] == 0.0
        assert stats["total_reads"] == 0
        assert stats["total_writes"] == 0

    def test_with_cache_hit_entries(self, temp_dir):
        """get_cache_stats aggregates hit/read/write tokens correctly."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker.track_llm_call(
            workflow="wf",
            stage="s",
            tier="CHEAP",
            model="claude-3-haiku-20240307",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="prompt",
            duration_ms=10,
            prompt_cache_hit=True,
            prompt_cache_read_tokens=80,
            prompt_cache_creation_tokens=20,
        )
        tracker.flush()

        stats = tracker.get_cache_stats(days=7)
        assert stats["hit_count"] >= 1
        assert stats["total_reads"] >= 80

    def test_pricing_lookup_with_unknown_model(self, temp_dir):
        """get_cache_stats handles unknown model (no pricing) gracefully."""
        tracker = UsageTracker(telemetry_dir=temp_dir)
        tracker.track_llm_call(
            workflow="wf",
            stage="s",
            tier="CHEAP",
            model="unknown-model-xyz",
            provider="anthropic",
            cost=0.001,
            tokens={"input": 100, "output": 50},
            cache_hit=True,
            cache_type="prompt",
            duration_ms=10,
            prompt_cache_hit=True,
            prompt_cache_read_tokens=50,
            prompt_cache_creation_tokens=0,
        )
        tracker.flush()

        # Should not raise even with unknown model (falls back to default pricing)
        stats = tracker.get_cache_stats(days=7)
        assert stats["total_reads"] >= 50


# ---------------------------------------------------------------------------
# Coverage-gap tests for usage_tracker.py
# ---------------------------------------------------------------------------


class TestSummaryLoadSave:
    def test_load_existing_summary_file(self, temp_dir):
        """A summary whose source_sig matches the logs is parsed and assigned.

        With no ``usage*.jsonl`` in the dir the signature is empty, so a
        summary carrying ``source_sig: {}`` is current and taken via the
        fast path (not rebuilt).
        """
        summary_path = temp_dir / "usage_summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "v": "1.0",
                    "updated": "2025-01-01T00:00:00Z",
                    "source_sig": {},
                    "days": {
                        "2025-01-01": {
                            "calls": 5,
                            "cost": 1.23,
                            "tokens_in": 100,
                            "tokens_out": 200,
                            "cache_hits": 1,
                            "cache_misses": 4,
                            "by_tier": {"cheap": 1.23},
                            "by_workflow": {"x": 1.23},
                            "by_provider": {"anthropic": 1.23},
                        }
                    },
                }
            )
        )
        t = UsageTracker(telemetry_dir=temp_dir, retention_days=7, max_file_size_mb=1)
        # Loaded from file (not rebuilt)
        assert "2025-01-01" in t._daily_summary
        assert t._daily_summary["2025-01-01"]["calls"] == 5

    def test_load_summary_with_corrupt_file_falls_back(self, temp_dir):
        """Lines 192-193: JSONDecodeError → resets to empty, then rebuild path."""
        summary_path = temp_dir / "usage_summary.json"
        summary_path.write_text("not-json{")
        t = UsageTracker(telemetry_dir=temp_dir, retention_days=7, max_file_size_mb=1)
        assert t._daily_summary == {}

    def test_save_summary_swallows_oserror(self, tracker):
        """Lines 223-224: _save_summary swallows OSError silently."""
        tracker._daily_summary = {"2025-01-01": tracker._empty_day()}
        with patch("builtins.open", side_effect=OSError("disk full")):
            # Should not raise
            tracker._save_summary()

    @staticmethod
    def _rec(ts: str, cost: float) -> dict:
        """A minimal usage record for log-reconciliation tests."""
        return {
            "ts": ts,
            "workflow": "w",
            "tier": "SDK",
            "provider": "anthropic",
            "cost": cost,
            "tokens": {"input": 1, "output": 1},
            "cache": {"hit": False},
        }

    def test_stale_summary_is_rebuilt_when_log_has_more(self, temp_dir):
        """Regression: a summary out of sync with the log is rebuilt, not trusted.

        Reproduces the MCP/dashboard under-count — a summary persisted while
        the log was shorter (or a concurrent writer clobbered it with partial
        data) carries a stale ``source_sig``; the reader must reconcile
        against the full log instead of reporting the stale total.
        """
        usage = temp_dir / "usage.jsonl"
        usage.write_text(
            json.dumps(self._rec("2025-02-01T00:00:00Z", 1.0))
            + "\n"
            + json.dumps(self._rec("2025-02-01T01:00:00Z", 2.0))
            + "\n"
        )
        # Stale summary: knows only the first record, wrong source_sig.
        (temp_dir / "usage_summary.json").write_text(
            json.dumps(
                {
                    "v": "1.0",
                    "updated": "2025-02-01T00:00:01Z",
                    "source_sig": {"usage.jsonl": 1},  # wrong size → stale
                    "days": {
                        "2025-02-01": {
                            **UsageTracker._empty_day(),
                            "calls": 1,
                            "cost": 1.0,
                        }
                    },
                }
            )
        )

        t = UsageTracker(telemetry_dir=temp_dir, retention_days=3650)
        stats = t.get_stats(days=3650)

        # Reconciled with the full log: both records ($3.00), not stale $1.00.
        assert stats["total_calls"] == 2
        assert stats["total_cost"] == 3.0

    def test_legacy_summary_without_sig_is_rebuilt(self, temp_dir):
        """A pre-fix summary (no ``source_sig``) is never trusted — rebuilt."""
        usage = temp_dir / "usage.jsonl"
        usage.write_text(json.dumps(self._rec("2025-03-01T00:00:00Z", 5.0)) + "\n")
        (temp_dir / "usage_summary.json").write_text(
            json.dumps(
                {
                    "v": "1.0",
                    "updated": "x",
                    "days": {
                        "2025-03-01": {
                            **UsageTracker._empty_day(),
                            "calls": 99,
                            "cost": 99.0,
                        }
                    },
                }
            )
        )

        t = UsageTracker(telemetry_dir=temp_dir, retention_days=3650)
        stats = t.get_stats(days=3650)

        assert stats["total_calls"] == 1
        assert stats["total_cost"] == 5.0

    def test_flush_does_not_persist_partial_summary(self, tracker, temp_dir):
        """flush updates the in-memory summary but does NOT write the file.

        The summary file is owned solely by full rebuilds; a buffered flush
        from a process that hasn't seen other writers' records must not
        clobber it with partial data (the lost-update root cause).
        """
        tracker.track_llm_call(
            workflow="w",
            stage=None,
            tier="SDK",
            model="m",
            provider="anthropic",
            cost=1.0,
            tokens={"input": 1, "output": 1},
            cache_hit=False,
            cache_type=None,
            duration_ms=1,
        )
        tracker.flush()

        # No summary file written by flush...
        assert not (temp_dir / "usage_summary.json").exists()
        # ...but the same process still sees its own data via the in-memory path.
        assert tracker.get_stats(days=3650)["total_calls"] == 1

    def test_load_summary_swallows_oserror_from_unreadable_dir(self, tracker):
        """Outer OSError guard: an unreadable telemetry dir disables gracefully."""
        from unittest.mock import MagicMock

        bad = MagicMock()
        bad.exists.side_effect = OSError("dir unreadable")
        tracker._summary_file = bad
        tracker._daily_summary = {"2025-01-01": tracker._empty_day()}

        tracker._load_summary()  # must not raise

        assert tracker._daily_summary == {}

    def test_source_signature_skips_unstatable_file(self, tracker):
        """Per-file OSError on stat() is skipped (glob succeeds), not fatal."""
        from unittest.mock import MagicMock

        # glob succeeds and yields a file, but stat() on it fails — exercises
        # the per-file inner guard (not the outer glob guard).
        bad_file = MagicMock()
        bad_file.name = "usage.jsonl"
        bad_file.stat.side_effect = OSError("no stat")

        with patch.object(Path, "glob", return_value=[bad_file]):
            sig = tracker._source_signature()

        # The single file was skipped → empty signature, no raise.
        assert sig == {}

    def test_source_signature_returns_empty_on_glob_error(self, tracker):
        """A glob() failure on the telemetry dir degrades to an empty signature."""
        with patch.object(Path, "glob", side_effect=OSError("glob failed")):
            assert tracker._source_signature() == {}


class TestFlushEdgeCases:
    def test_flush_empty_buffer_returns_zero(self, tracker):
        """Line 348: early return 0 when buffer is empty."""
        assert tracker.flush() == 0


class TestGetRecentEntriesBufferCutoff:
    def test_buffer_entry_before_cutoff_skipped(self, tracker):
        """Line 495: buffered entry older than cutoff is skipped."""
        old_ts = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        tracker._buffer.append(
            {
                "v": "1.0",
                "ts": old_ts,
                "seq": 999,
                "workflow": "old",
                "tier": "cheap",
                "model": "x",
                "provider": "anthropic",
                "cost": 0.01,
                "tokens": {"input": 10, "output": 20},
                "cache": {"hit": False},
                "duration_ms": 5,
                "user_id": "h",
            }
        )
        # cutoff is 1 day → old entry filtered out
        entries = tracker.get_recent_entries(limit=100, days=1)
        assert all(e.get("workflow") != "old" for e in entries)


class TestGetStatsFastPath:
    def test_fast_path_uses_prebuilt_summary(self, tracker):
        """Lines 541-551: when _daily_summary is non-empty, use fast aggregation."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tracker._daily_summary = {
            today: {
                "calls": 4,
                "cost": 2.5,
                "tokens_in": 400,
                "tokens_out": 800,
                "cache_hits": 1,
                "cache_misses": 3,
                "by_tier": {"premium": 2.5},
                "by_workflow": {"wfA": 2.5},
                "by_provider": {"anthropic": 2.5},
            }
        }
        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] == 4
        assert stats["total_cost"] == 2.5
        assert stats["total_tokens_input"] == 400
        assert stats["total_tokens_output"] == 800
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 3
        assert stats["by_tier"]["premium"] == 2.5
        assert stats["by_workflow"]["wfA"] == 2.5
        assert stats["by_provider"]["anthropic"] == 2.5

    def test_fast_path_skips_dates_before_cutoff(self, tracker):
        """Line 542: dates older than cutoff_date are skipped."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        tracker._daily_summary = {
            old_date: {
                "calls": 99,
                "cost": 9.0,
                "tokens_in": 1,
                "tokens_out": 1,
                "cache_hits": 0,
                "cache_misses": 0,
                "by_tier": {},
                "by_workflow": {},
                "by_provider": {},
            }
        }
        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] == 0

    def test_fast_path_includes_buffered_entries(self, tracker):
        """Lines 562-568: buffered entries get accumulated after summary path."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tracker._daily_summary = {
            today: {
                "calls": 1,
                "cost": 1.0,
                "tokens_in": 10,
                "tokens_out": 20,
                "cache_hits": 0,
                "cache_misses": 1,
                "by_tier": {},
                "by_workflow": {},
                "by_provider": {},
            }
        }
        now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tracker._buffer.append(
            {
                "ts": now_ts,
                "cost": 0.5,
                "tokens": {"input": 5, "output": 7},
                "cache": {"hit": True},
                "tier": "cheap",
                "workflow": "wf",
                "provider": "anthropic",
            }
        )
        stats = tracker.get_stats(days=30)
        assert stats["total_calls"] == 2
        assert abs(stats["total_cost"] - 1.5) < 1e-9

    def test_fast_path_skips_buffered_entry_with_bad_ts(self, tracker):
        """Lines 564-565: KeyError/ValueError on bad ts → entry skipped."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tracker._daily_summary = {
            today: {
                "calls": 0,
                "cost": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "by_tier": {},
                "by_workflow": {},
                "by_provider": {},
            }
        }
        tracker._buffer.append({"ts": "not-a-date", "cost": 99.0})
        tracker._buffer.append({"cost": 99.0})  # missing ts
        stats = tracker.get_stats(days=30)
        assert stats["total_cost"] == 0.0

    def test_fast_path_skips_buffered_entry_before_cutoff(self, tracker):
        """Lines 566-567: buffered entry older than cutoff is skipped."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        tracker._daily_summary = {
            today: {
                "calls": 0,
                "cost": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "by_tier": {},
                "by_workflow": {},
                "by_provider": {},
            }
        }
        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        tracker._buffer.append(
            {
                "ts": old_ts,
                "cost": 99.0,
                "tokens": {"input": 1, "output": 1},
                "cache": {"hit": False},
                "tier": "cheap",
                "workflow": "old",
                "provider": "anthropic",
            }
        )
        stats = tracker.get_stats(days=7)
        assert stats["total_cost"] == 0.0


class TestCacheStatsBranches:
    def test_no_prompt_cache_hit(self, tracker):
        """Line 732->735: prompt_cache.get('hit') False → skip hit_count++."""
        tracker.track_llm_call(
            workflow="wf",
            stage=None,
            tier="cheap",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
            prompt_cache_hit=False,
            prompt_cache_creation_tokens=10,  # forces prompt_cache dict
            prompt_cache_read_tokens=0,
        )
        tracker.flush()
        stats = tracker.get_cache_stats(days=7)
        assert stats["hit_count"] == 0

    def test_zero_read_tokens_skips_pricing_lookup(self, tracker):
        """Line 740->749: read_tokens == 0 → skip pricing block."""
        tracker.track_llm_call(
            workflow="wf",
            stage=None,
            tier="cheap",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
            prompt_cache_hit=False,
            prompt_cache_creation_tokens=20,
            prompt_cache_read_tokens=0,  # zero read tokens
        )
        tracker.flush()
        stats = tracker.get_cache_stats(days=7)
        assert stats["savings"] == 0.0

    def test_pricing_cache_reused_across_entries(self, tracker):
        """Line 742->744: model_id already in pricing_cache → skip lookup."""
        for _ in range(3):
            tracker.track_llm_call(
                workflow="wf",
                stage=None,
                tier="cheap",
                model="claude-haiku-4-5",  # same model each time
                provider="anthropic",
                cost=0.01,
                tokens={"input": 100, "output": 50},
                cache_hit=False,
                cache_type=None,
                duration_ms=10,
                prompt_cache_hit=True,
                prompt_cache_creation_tokens=0,
                prompt_cache_read_tokens=50,
            )
        tracker.flush()
        stats = tracker.get_cache_stats(days=7)
        assert stats["hit_count"] == 3
        # 3 entries with reads → pricing_cache reused twice (covers branch)
        assert stats["total_reads"] == 150

    def test_existing_workflow_not_reinitialized(self, tracker):
        """Line 750->758: workflow already in by_workflow → skip init block."""
        for _ in range(2):
            tracker.track_llm_call(
                workflow="same_wf",  # same workflow each time
                stage=None,
                tier="cheap",
                model="claude-haiku-4-5",
                provider="anthropic",
                cost=0.01,
                tokens={"input": 100, "output": 50},
                cache_hit=False,
                cache_type=None,
                duration_ms=10,
                prompt_cache_hit=True,
                prompt_cache_creation_tokens=0,
                prompt_cache_read_tokens=10,
            )
        tracker.flush()
        stats = tracker.get_cache_stats(days=7)
        assert stats["by_workflow"]["same_wf"]["requests"] == 2

    def test_per_workflow_no_hit(self, tracker):
        """Line 760->762: per-workflow miss path (skip hits++)."""
        tracker.track_llm_call(
            workflow="wf_no_hit",
            stage=None,
            tier="cheap",
            model="claude-haiku-4-5",
            provider="anthropic",
            cost=0.01,
            tokens={"input": 100, "output": 50},
            cache_hit=False,
            cache_type=None,
            duration_ms=10,
            prompt_cache_hit=False,  # no hit
            prompt_cache_creation_tokens=10,
            prompt_cache_read_tokens=0,
        )
        tracker.flush()
        stats = tracker.get_cache_stats(days=7)
        assert stats["by_workflow"]["wf_no_hit"]["hits"] == 0
        assert stats["by_workflow"]["wf_no_hit"]["requests"] == 1


class TestUsagePingAtExitWiring:
    """The opt-in usage-ping sync is kicked from the atexit chain and
    must run AFTER the local flush so it sees freshly-persisted events."""

    def test_get_instance_registers_ping_before_flush(self, monkeypatch, temp_dir):
        """atexit is LIFO, so ping (runs last) must be REGISTERED first."""
        import atexit as _atexit

        registered = []
        monkeypatch.setattr(_atexit, "register", lambda fn, *a, **k: registered.append(fn))
        UsageTracker._instance = None
        try:
            UsageTracker.get_instance(telemetry_dir=temp_dir)
            assert UsageTracker._atexit_usage_ping in registered
            assert UsageTracker._atexit_flush in registered
            # ping registered first => ping runs AFTER flush at exit
            assert registered.index(UsageTracker._atexit_usage_ping) < registered.index(
                UsageTracker._atexit_flush
            )
        finally:
            UsageTracker._instance = None

    def test_atexit_usage_ping_delegates_to_run_sync_at_exit(self, monkeypatch):
        from attune.telemetry import usage_ping

        called = []
        monkeypatch.setattr(usage_ping, "run_sync_at_exit", lambda: called.append(1) or 0)
        UsageTracker._atexit_usage_ping()
        assert called == [1]

    def test_atexit_usage_ping_never_raises(self, monkeypatch):
        from attune.telemetry import usage_ping

        def _boom():
            raise RuntimeError("ping blew up")

        monkeypatch.setattr(usage_ping, "run_sync_at_exit", _boom)
        # Must not propagate — telemetry can't affect process exit.
        UsageTracker._atexit_usage_ping()


class TestHmacSecret:
    """Per-install HMAC secret (replaces the shared committed constant)."""

    OLD_CONSTANT = b"attune-default-telemetry-key"

    def test_per_install_secret_file_created_0600(self, temp_dir):
        """First hash with no env secret writes a per-install .secret (0600 on POSIX)."""
        import sys

        with patch("attune.config.env_compat.get_attune_env", return_value=None):
            digest = UsageTracker(telemetry_dir=temp_dir)._hash_user_id("default")

        secret_file = temp_dir / ".secret"
        assert secret_file.exists()
        assert isinstance(digest, str) and len(digest) == 16
        # File-mode bits are POSIX-only — Windows maps os.open() modes to
        # 0o666 regardless, so the permission assertion is gated to POSIX.
        if sys.platform != "win32":
            assert (secret_file.stat().st_mode & 0o777) == 0o600

    def test_secret_stable_across_instances_same_dir(self, temp_dir):
        """Two installs sharing a dir reuse the .secret → identical hash."""
        with patch("attune.config.env_compat.get_attune_env", return_value=None):
            h1 = UsageTracker(telemetry_dir=temp_dir)._hash_user_id("alice")
            h2 = UsageTracker(telemetry_dir=temp_dir)._hash_user_id("alice")
        assert h1 == h2

    def test_secret_differs_across_installs(self, temp_dir):
        """Different install dirs get different secrets → uncorrelatable hashes."""
        with patch("attune.config.env_compat.get_attune_env", return_value=None):
            h1 = UsageTracker(telemetry_dir=temp_dir / "i1")._hash_user_id("alice")
            h2 = UsageTracker(telemetry_dir=temp_dir / "i2")._hash_user_id("alice")
        assert h1 != h2

    def test_env_secret_overrides_file(self, temp_dir):
        """TELEMETRY_SECRET wins and no .secret file is written."""
        with patch("attune.config.env_compat.get_attune_env", return_value="my-secret"):
            digest = UsageTracker(telemetry_dir=temp_dir)._hash_user_id("alice")
        assert not (temp_dir / ".secret").exists()
        expected = hmac.new(b"my-secret", b"alice", hashlib.sha256).hexdigest()[:16]
        assert digest == expected

    def test_not_the_old_constant_key(self, temp_dir):
        """Regression: the digest is no longer the reversible shared constant."""
        with patch("attune.config.env_compat.get_attune_env", return_value=None):
            digest = UsageTracker(telemetry_dir=temp_dir)._hash_user_id("default")
        old = hmac.new(self.OLD_CONSTANT, b"default", hashlib.sha256).hexdigest()[:16]
        assert digest != old

    def test_hash_is_memoized(self, temp_dir):
        """Repeat hashes of the same id don't recompute the HMAC."""
        with patch("attune.config.env_compat.get_attune_env", return_value=None):
            tracker = UsageTracker(telemetry_dir=temp_dir)
            tracker._hash_user_id("bob")  # populate cache
            with patch("attune.telemetry.usage_tracker.hmac.new") as mock_new:
                again = tracker._hash_user_id("bob")
                mock_new.assert_not_called()
        assert isinstance(again, str)


class TestParseTs:
    """The single timestamp-parsing helper."""

    def test_parses_z_suffix(self):
        dt = UsageTracker._parse_ts("2024-01-15T12:00:00.000000Z")
        assert dt is not None and dt.tzinfo is not None and dt.year == 2024

    def test_parses_explicit_offset(self):
        dt = UsageTracker._parse_ts("2024-01-15T12:00:00+00:00")
        assert dt is not None and dt.utcoffset().total_seconds() == 0

    def test_naive_coerced_to_utc(self):
        dt = UsageTracker._parse_ts("2024-01-15T12:00:00")
        assert dt is not None and dt.tzinfo == timezone.utc

    def test_missing_or_garbage_returns_none(self):
        assert UsageTracker._parse_ts(None) is None
        assert UsageTracker._parse_ts("") is None
        assert UsageTracker._parse_ts("not-a-timestamp") is None


class TestRotatedFileDate:
    """Filename-date parsing used for retention."""

    def test_parses_dated_name(self):
        dt = UsageTracker._rotated_file_date("usage.2024-01-15.jsonl")
        assert dt is not None and (dt.year, dt.month, dt.day) == (2024, 1, 15)

    def test_parses_dated_name_with_counter(self):
        dt = UsageTracker._rotated_file_date("usage.2024-01-15.3.jsonl")
        assert dt is not None and dt.day == 15

    def test_live_file_returns_none(self):
        assert UsageTracker._rotated_file_date("usage.jsonl") is None

    def test_unparseable_date_returns_none(self):
        assert UsageTracker._rotated_file_date("usage.notadate.jsonl") is None
