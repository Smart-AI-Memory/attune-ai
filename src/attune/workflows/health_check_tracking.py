"""Health Check Tracking and Persistence

Trend tracking, history saving, and VS Code extension
health.json generation for health check workflows.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import logging
from pathlib import Path

from attune.security.path_validation import _validate_file_path

from .health_check_models import HealthCheckReport

logger = logging.getLogger(__name__)


def get_trend_comparison(
    current_score: float,
    tracking_dir: Path,
) -> str:
    """Compare current score with last check.

    Args:
        current_score: Current health score
        tracking_dir: Directory containing history.jsonl

    Returns:
        Trend description

    """
    history_file = tracking_dir / "history.jsonl"

    if not history_file.exists():
        return "No historical data"

    # Read last score from history
    try:
        with history_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            if len(lines) < 2:
                return "First baseline established"

            # Get second-to-last entry (last is current)
            previous_entry = json.loads(lines[-2])
            previous_score = previous_entry.get("overall_health_score", 0.0)

            delta = current_score - previous_score

            if abs(delta) < 1.0:
                return f"Stable (~{previous_score:.1f})"
            if delta > 0:
                return f"Improving (+{delta:.1f} from {previous_score:.1f})"
            return f"Declining ({delta:.1f} from {previous_score:.1f})"

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("Error reading tracking history: %s", e)
        return "Unable to determine trend"


def save_tracking_history(
    report: HealthCheckReport,
    tracking_dir: Path,
) -> None:
    """Save health check report to tracking history.

    Args:
        report: Health check report to save
        tracking_dir: Directory for history.jsonl

    """
    history_file = tracking_dir / "history.jsonl"

    try:
        # Append to history file (JSONL format)
        with history_file.open("a", encoding="utf-8") as f:
            entry = {
                "timestamp": report.timestamp,
                "mode": report.mode,
                "overall_health_score": (report.overall_health_score),
                "grade": report.grade,
                "execution_time": report.execution_time,
                "category_scores": [
                    {"name": cat.name, "score": cat.score} for cat in report.category_scores
                ],
            }
            f.write(json.dumps(entry) + "\n")

        logger.info("Saved health check to tracking history: %s", history_file)

    except OSError as e:
        logger.error("Failed to save tracking history: %s", e)


def save_health_json(
    report: HealthCheckReport,
    project_root: Path,
) -> None:
    """Save health check report to .attune/health.json.

    This creates the health.json file for health check reporting.

    Args:
        report: Health check report to save
        project_root: Project root directory

    """
    health_file = project_root / ".attune" / "health.json"

    try:
        # Ensure .attune directory exists
        health_file.parent.mkdir(parents=True, exist_ok=True)

        # Extract metrics from category scores
        lint_errors = 0
        type_errors = 0
        security_high = 0
        security_medium = 0
        security_low = 0
        test_passed = 0
        test_failed = 0
        test_total = 0
        coverage_pct = 0.0

        for category in report.category_scores:
            if category.name == "Quality":
                quality_score = category.raw_metrics.get("quality_score", 10.0)
                lint_errors = max(0, int((10 - quality_score) * 5))

            elif category.name == "Security":
                security_high = category.raw_metrics.get("critical_issues", 0)
                security_medium = category.raw_metrics.get("high_issues", 0)
                security_low = category.raw_metrics.get("medium_issues", 0)

            elif category.name == "Coverage":
                coverage_pct = category.score
                if coverage_pct > 70:
                    test_total = 100
                    test_passed = int(coverage_pct)
                    test_failed = test_total - test_passed

        # Build health data in VS Code extension format
        health_data = {
            "score": int(report.overall_health_score),
            "lint": {
                "errors": lint_errors,
                "warnings": 0,
            },
            "types": {"errors": type_errors},
            "security": {
                "high": security_high,
                "medium": security_medium,
                "low": security_low,
            },
            "tests": {
                "passed": test_passed,
                "failed": test_failed,
                "total": test_total,
                "coverage": int(coverage_pct),
            },
            "tech_debt": {
                "total": 0,
                "todos": 0,
                "fixmes": 0,
                "hacks": 0,
            },
            "timestamp": report.timestamp,
            "mode": report.mode,
            "grade": report.grade,
        }

        # Write health.json
        validated_health_file = _validate_file_path(str(health_file))
        with validated_health_file.open("w", encoding="utf-8") as f:
            json.dump(health_data, f, indent=2)

        logger.info("Saved health data to %s for VS Code extension", validated_health_file)

    except OSError as e:
        logger.warning("Failed to save health.json (file system error): %s", e)
    except (TypeError, ValueError) as e:
        logger.error("Failed to save health.json (serialization error): %s", e)
    except Exception as e:  # noqa: BLE001
        # INTENTIONAL: Saving health data should never crash
        # a health check
        logger.warning("Failed to save health.json (unexpected error): %s", e)
