"""CLI commands for cost tracking.

Provides `attune costs`, `attune costs today`, `attune costs export`,
and `attune costs reset` commands for viewing API cost data and savings
from smart model routing.

Wraps the existing CostTracker in src/attune/cost_tracker.py.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import csv
import json
import logging
from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from attune.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


def cmd_costs(args: Namespace) -> int:
    """Show cost report for recent period.

    Args:
        args: Parsed arguments with days, json, and workflow flags.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.cost_tracker import CostTracker

    try:
        tracker = CostTracker()
        days = getattr(args, "days", 7)
        workflow = getattr(args, "workflow", None)
        as_json = getattr(args, "json", False)

        if workflow:
            return _costs_by_workflow(tracker, days, workflow, as_json)

        if as_json:
            summary = tracker.get_summary(days)
            print(json.dumps(summary, indent=2))
        else:
            print(tracker.get_report(days))

        return 0
    except OSError as e:
        logger.error("Failed to read cost data: %s", e)
        print(f"Error reading cost data: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # Broad by contract: the docstring promises exit 1 on failure, and
        # corrupt tracker data raises KeyError/TypeError, not OSError.
        logger.exception("Unexpected error generating cost report")
        print(f"Error generating cost report: {e}")
        return 1


def _costs_by_workflow(
    tracker: CostTracker,
    days: int,
    workflow: str,
    as_json: bool,
) -> int:
    """Filter cost report by workflow name.

    Args:
        tracker: CostTracker instance.
        days: Number of days to include.
        workflow: Workflow name to filter by (matched against task_type).
        as_json: If True, output as JSON.

    Returns:
        0 on success.

    """
    from datetime import datetime, timedelta

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    # Load full request history to filter by task_type
    tracker._load_requests()
    all_requests = list(tracker.data.get("requests", []))
    all_requests.extend(tracker._buffer)

    # Filter by workflow name in task_type field
    filtered = [
        r for r in all_requests if r["timestamp"] >= cutoff and workflow in r.get("task_type", "")
    ]

    total_actual = sum(r["actual_cost"] for r in filtered)
    total_baseline = sum(r["baseline_cost"] for r in filtered)
    total_savings = sum(r["savings"] for r in filtered)
    savings_pct = round((total_savings / total_baseline) * 100, 1) if total_baseline > 0 else 0.0

    result = {
        "workflow": workflow,
        "days": days,
        "requests": len(filtered),
        "actual_cost": round(total_actual, 6),
        "baseline_cost": round(total_baseline, 6),
        "savings": round(total_savings, 6),
        "savings_percent": savings_pct,
    }

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nCost Report: {workflow}")
        print(f"Last {days} days")
        print("-" * 40)
        print(f"  Requests:        {len(filtered):,}")
        print(f"  Actual cost:     ${total_actual:.4f}")
        from attune.cost_tracker import _baseline_label

        print(f"  {_baseline_label():<16} ${total_baseline:.4f}")
        print(f"  Saved:           ${total_savings:.4f} ({savings_pct}%)")
        print()

    return 0


def cmd_costs_today(args: Namespace) -> int:
    """Show today's cost summary.

    Args:
        args: Parsed arguments (no additional flags needed).

    Returns:
        0 on success, 1 on failure.

    """
    from attune.cost_tracker import CostTracker

    try:
        tracker = CostTracker()
        today = tracker.get_today()

        requests = today.get("requests", 0)
        actual = today.get("actual_cost", 0)
        baseline = today.get("baseline_cost", 0)
        savings = today.get("savings", 0)
        pct = round((savings / baseline) * 100, 1) if baseline > 0 else 0.0

        print(
            f"Today: {requests} requests | "
            f"${actual:.4f} actual | "
            f"${baseline:.4f} baseline | "
            f"saved ${savings:.4f} ({pct}%)",
        )
        return 0
    except OSError as e:
        logger.error("Failed to read cost data: %s", e)
        print(f"Error reading cost data: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # Broad by contract: the docstring promises exit 1 on failure, and
        # corrupt tracker data raises KeyError/TypeError, not OSError.
        logger.exception("Unexpected error reading today's cost data")
        print(f"Error reading cost data: {e}")
        return 1


def cmd_costs_export(args: Namespace) -> int:
    """Export cost data to file.

    Args:
        args: Parsed arguments with output, format, and days.

    Returns:
        0 on success, 1 on failure.

    """
    from attune.cost_tracker import CostTracker
    from attune.security.path_validation import _validate_file_path

    try:
        validated_path = _validate_file_path(args.output)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    try:
        tracker = CostTracker()
        days = getattr(args, "days", 30)
        fmt = getattr(args, "format", "json")

        if fmt == "csv":
            _export_csv(tracker, days, validated_path)
        else:
            _export_json(tracker, days, validated_path)

        print(f"Exported to {validated_path}")
        return 0
    except PermissionError as e:
        logger.error("Permission denied writing to %s: %s", args.output, e)
        print(f"Error: Permission denied: {e}")
        return 1
    except OSError as e:
        logger.error("Failed to export cost data: %s", e)
        print(f"Error exporting cost data: {e}")
        return 1
    except Exception as e:  # noqa: BLE001
        # Broad by contract: the docstring promises exit 1 on failure, and
        # corrupt tracker data raises KeyError/TypeError, not OSError.
        logger.exception("Unexpected error exporting cost data")
        print(f"Error exporting cost data: {e}")
        return 1


def _export_json(tracker: CostTracker, days: int, path: Path) -> None:
    """Export cost summary as JSON.

    Args:
        tracker: CostTracker instance.
        days: Number of days to include.
        path: Validated Path object.

    """
    summary = tracker.get_summary(days)
    # Serialize before opening: a TypeError from corrupt data must not
    # leave a truncated file or destroy a previously valid export.
    payload = json.dumps(summary, indent=2)
    path.write_text(payload, encoding="utf-8")


def _export_csv(tracker: CostTracker, days: int, path: Path) -> None:
    """Export daily cost totals as CSV.

    Args:
        tracker: CostTracker instance.
        days: Number of days to include.
        path: Validated Path object.

    """
    from datetime import datetime, timedelta

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    daily_totals = tracker.data.get("daily_totals", {})

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "date",
                "requests",
                "input_tokens",
                "output_tokens",
                "actual_cost",
                "baseline_cost",
                "savings",
            ],
        )

        for date in sorted(daily_totals.keys()):
            if date >= cutoff:
                row = daily_totals[date]
                writer.writerow(
                    [
                        date,
                        row.get("requests", 0),
                        row.get("input_tokens", 0),
                        row.get("output_tokens", 0),
                        row.get("actual_cost", 0),
                        row.get("baseline_cost", 0),
                        row.get("savings", 0),
                    ],
                )


def cmd_costs_reset(args: Namespace) -> int:
    """Clear all cost tracking data.

    Args:
        args: Parsed arguments with confirm flag.

    Returns:
        0 on success, 1 on failure.

    """
    if not getattr(args, "confirm", False):
        print("This will delete all cost tracking data.")
        print("Run with --confirm to proceed.")
        return 1

    storage_dir = Path(".attune")
    files_to_delete = [
        storage_dir / "costs.json",
        storage_dir / "costs.jsonl",
        storage_dir / "costs_summary.json",
    ]

    deleted = 0
    for file_path in files_to_delete:
        try:
            if file_path.exists():
                file_path.unlink()
                deleted += 1
        except OSError as e:
            logger.error("Failed to delete %s: %s", file_path, e)
            print(f"Error deleting {file_path}: {e}")
            return 1

    print(f"Cost data cleared ({deleted} file(s) removed).")
    return 0


__all__ = ["cmd_costs", "cmd_costs_export", "cmd_costs_reset", "cmd_costs_today"]
