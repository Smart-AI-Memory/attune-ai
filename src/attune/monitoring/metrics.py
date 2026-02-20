"""Telemetry metrics collection for alert evaluation.

Reads JSONL telemetry files and aggregates metrics over a 24-hour
window for use by the alert engine threshold checks.

Copyright 2025-2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# Default metric values when no data is available
_EMPTY_METRICS: dict[str, float] = {
    "daily_cost": 0.0,
    "error_rate": 0.0,
    "avg_latency": 0.0,
    "token_usage": 0,
}


def collect_metrics(telemetry_dir: Path) -> dict[str, float]:
    """Collect current telemetry metrics from JSONL files.

    Reads from telemetry files and calculates:
    - daily_cost: Total cost in last 24 hours
    - error_rate: Percentage of errors
    - avg_latency: Average latency in ms
    - token_usage: Total tokens in last 24 hours

    Args:
        telemetry_dir: Path to directory containing usage.jsonl

    Returns:
        Dictionary of metric name to current value
    """
    usage_file = telemetry_dir / "usage.jsonl"

    if not usage_file.exists():
        logger.debug("telemetry_file_not_found", path=str(usage_file))
        return dict(_EMPTY_METRICS)

    # Read last 24 hours of data
    cutoff = datetime.now() - timedelta(hours=24)
    total_cost = 0.0
    total_tokens = 0
    total_latency = 0.0
    total_calls = 0
    error_calls = 0

    try:
        with open(usage_file) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    timestamp = datetime.fromisoformat(entry.get("timestamp", "2000-01-01"))
                    if timestamp < cutoff:
                        continue

                    total_calls += 1
                    total_cost += entry.get("cost", 0.0)
                    total_tokens += entry.get("tokens", {}).get("total", 0)
                    total_latency += entry.get("duration_ms", 0)

                    if entry.get("error"):
                        error_calls += 1
                except (json.JSONDecodeError, KeyError):
                    continue
    except (OSError, PermissionError) as e:
        logger.warning("telemetry_read_error", error=str(e))
        return dict(_EMPTY_METRICS)

    return {
        "daily_cost": total_cost,
        "error_rate": (error_calls / total_calls * 100) if total_calls > 0 else 0.0,
        "avg_latency": (total_latency / total_calls) if total_calls > 0 else 0.0,
        "token_usage": total_tokens,
    }
