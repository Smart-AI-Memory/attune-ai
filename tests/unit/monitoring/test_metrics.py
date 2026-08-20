"""Tests for telemetry metrics collection.

Covers the aggregation edges in ``attune.monitoring.metrics.collect_metrics``:
missing file, blank lines, stale (outside-window) entries, malformed JSON
lines, and unreadable files.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from attune.monitoring.metrics import _EMPTY_METRICS, collect_metrics


@pytest.fixture
def temp_telemetry_dir():
    """Create a temporary telemetry directory (empty by default)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _write_usage_lines(telemetry_dir: Path, lines: list[str]) -> Path:
    usage_file = telemetry_dir / "usage.jsonl"
    with usage_file.open("w") as f:
        f.write("\n".join(lines))
        f.write("\n")
    return usage_file


class TestCollectMetricsMissingFile:
    """No usage.jsonl present."""

    def test_returns_empty_metrics_when_file_missing(self, temp_telemetry_dir):
        result = collect_metrics(temp_telemetry_dir)

        assert result == dict(_EMPTY_METRICS)


class TestCollectMetricsBlankLines:
    """Blank lines in the JSONL file are skipped, not counted as calls."""

    def test_blank_lines_are_skipped(self, temp_telemetry_dir):
        now = datetime.now().isoformat()
        _write_usage_lines(
            temp_telemetry_dir,
            [
                "",
                "   ",
                json.dumps(
                    {
                        "timestamp": now,
                        "cost": 2.0,
                        "tokens": {"total": 100},
                        "duration_ms": 50,
                    }
                ),
                "",
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        # Only the single real entry counted -> avg_latency == its duration.
        assert result["daily_cost"] == 2.0
        assert result["token_usage"] == 100
        assert result["avg_latency"] == 50
        assert result["error_rate"] == 0.0


class TestCollectMetricsStaleEntries:
    """Entries older than the 24h cutoff are excluded from aggregation."""

    def test_entries_outside_24h_window_are_excluded(self, temp_telemetry_dir):
        stale_timestamp = (datetime.now() - timedelta(hours=48)).isoformat()
        fresh_timestamp = datetime.now().isoformat()
        _write_usage_lines(
            temp_telemetry_dir,
            [
                json.dumps(
                    {
                        "timestamp": stale_timestamp,
                        "cost": 999.0,
                        "tokens": {"total": 99999},
                        "duration_ms": 99999,
                    }
                ),
                json.dumps(
                    {
                        "timestamp": fresh_timestamp,
                        "cost": 1.0,
                        "tokens": {"total": 10},
                        "duration_ms": 20,
                    }
                ),
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        # Stale entry's huge values must not leak into the aggregate.
        assert result["daily_cost"] == 1.0
        assert result["token_usage"] == 10
        assert result["avg_latency"] == 20

    def test_all_entries_stale_yields_zero_calls_defaults(self, temp_telemetry_dir):
        stale_timestamp = (datetime.now() - timedelta(hours=72)).isoformat()
        _write_usage_lines(
            temp_telemetry_dir,
            [
                json.dumps(
                    {
                        "timestamp": stale_timestamp,
                        "cost": 5.0,
                        "tokens": {"total": 500},
                        "duration_ms": 300,
                    }
                )
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        # total_calls stays 0 -> error_rate/avg_latency fall back to 0.0,
        # but cost/tokens defaults come from the (unincremented) accumulators.
        assert result["daily_cost"] == 0.0
        assert result["error_rate"] == 0.0
        assert result["avg_latency"] == 0.0
        assert result["token_usage"] == 0


class TestCollectMetricsMalformedLines:
    """Malformed JSON and entries missing required keys are skipped."""

    def test_invalid_json_line_is_skipped(self, temp_telemetry_dir):
        now = datetime.now().isoformat()
        _write_usage_lines(
            temp_telemetry_dir,
            [
                "{not valid json",
                json.dumps(
                    {
                        "timestamp": now,
                        "cost": 4.0,
                        "tokens": {"total": 40},
                        "duration_ms": 10,
                    }
                ),
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        assert result["daily_cost"] == 4.0
        assert result["token_usage"] == 40

    def test_entry_missing_timestamp_key_falls_back_and_is_excluded(self, temp_telemetry_dir):
        # entry.get("timestamp", "2000-01-01") means a missing timestamp
        # parses to a stale date far outside the 24h window -- excluded,
        # not raising KeyError (the get() default handles it).
        _write_usage_lines(
            temp_telemetry_dir,
            [
                json.dumps({"cost": 7.0, "tokens": {"total": 70}, "duration_ms": 15}),
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        assert result == dict(_EMPTY_METRICS)

    def test_entry_with_non_dict_tokens_is_skipped(self, temp_telemetry_dir):
        # A non-dict `tokens` used to break `.get("total", 0)` with an
        # AttributeError that escaped (JSONDecodeError, KeyError) and
        # killed the whole aggregation. This test previously PINNED that
        # crash as "current behavior (production bug candidate)"; the
        # library review confirmed and fixed it, so the row is now
        # skipped like every other malformed shape.
        now = datetime.now().isoformat()
        _write_usage_lines(
            temp_telemetry_dir,
            [
                json.dumps({"timestamp": now, "cost": 1.0, "tokens": 5, "duration_ms": 10}),
                json.dumps(
                    {
                        "timestamp": now,
                        "cost": 2.0,
                        "tokens": {"total": 7},
                        "duration_ms": 20,
                    }
                ),
            ],
        )

        result = collect_metrics(temp_telemetry_dir)

        # The bad row contributes no tokens but does not abort the read;
        # the good row is still aggregated.
        assert result["token_usage"] == 7
        assert result["daily_cost"] == 3.0


class TestCollectMetricsReadError:
    """OSError/PermissionError while reading the file degrades to empty metrics."""

    def test_permission_error_returns_empty_metrics(self, temp_telemetry_dir):
        _write_usage_lines(
            temp_telemetry_dir, [json.dumps({"timestamp": datetime.now().isoformat()})]
        )

        with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
            result = collect_metrics(temp_telemetry_dir)

        assert result == dict(_EMPTY_METRICS)

    def test_os_error_returns_empty_metrics(self, temp_telemetry_dir):
        _write_usage_lines(
            temp_telemetry_dir, [json.dumps({"timestamp": datetime.now().isoformat()})]
        )

        with patch("pathlib.Path.open", side_effect=OSError("disk error")):
            result = collect_metrics(temp_telemetry_dir)

        assert result == dict(_EMPTY_METRICS)


class TestCollectMetricsErrorRate:
    """error_rate percentage calculation across mixed error/success entries."""

    def test_error_rate_percentage(self, temp_telemetry_dir):
        now = datetime.now().isoformat()
        entries = [
            {"timestamp": now, "cost": 1.0, "tokens": {"total": 10}, "duration_ms": 100},
            {
                "timestamp": now,
                "cost": 1.0,
                "tokens": {"total": 10},
                "duration_ms": 100,
                "error": True,
            },
            {
                "timestamp": now,
                "cost": 1.0,
                "tokens": {"total": 10},
                "duration_ms": 100,
                "error": True,
            },
            {"timestamp": now, "cost": 1.0, "tokens": {"total": 10}, "duration_ms": 100},
        ]
        _write_usage_lines(temp_telemetry_dir, [json.dumps(e) for e in entries])

        result = collect_metrics(temp_telemetry_dir)

        assert result["error_rate"] == 50.0
        assert result["avg_latency"] == 100
        assert result["daily_cost"] == 4.0
        assert result["token_usage"] == 40
