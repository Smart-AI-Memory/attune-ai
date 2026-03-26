"""Morning Briefing Workflow for Attune AI.

Start-of-day developer briefing with patterns, debt, and focus areas.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from attune.security.path_validation import _validate_file_path


def _wc():
    """Late-resolve the workflow_commands facade for patchable helper access."""
    return sys.modules["attune.workflow_commands"]


def _print_patterns_section(patterns: dict) -> int:
    """Print the patterns summary section. Returns total bug count."""
    print("PATTERNS LEARNED")
    print("-" * 40)

    debugging = patterns.get("debugging", [])
    total_bugs = len(debugging)
    resolved_bugs = sum(1 for p in debugging if p.get("status") == "resolved")

    print(f"  Bug patterns:        {total_bugs} ({resolved_bugs} resolved)")
    print(f"  Security decisions:  {len(patterns.get('security', []))}")
    print(f"  Inspection patterns: {len(patterns.get('inspection', []))}")

    week_ago = datetime.now() - timedelta(days=7)
    recent_bugs = []
    for bug in debugging:
        try:
            timestamp = bug.get("timestamp", bug.get("resolved_at", ""))
            if timestamp:
                bug_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if bug_date.replace(tzinfo=None) > week_ago:
                    recent_bugs.append(bug)
        except (ValueError, TypeError):
            pass

    if recent_bugs:
        print(f"\n  New this week: {len(recent_bugs)} patterns")
        for bug in recent_bugs[:3]:
            print(f"    - {bug.get('bug_type', '?')}: {bug.get('root_cause', '?')[:40]}")

    return total_bugs


_TREND_MESSAGES = {
    "increasing": "  Trending UP - Consider allocating time for cleanup",
    "decreasing": "  Trending DOWN - Great progress!",
    "stable": "  Stable - Holding steady",
    "unknown": "  Run 'attune workflow run code-review' to start tracking",
    "insufficient_data": "  Not enough data yet - keep coding!",
}


def _print_tech_debt_section(wc: Any, patterns_dir: str) -> str:
    """Print the tech debt trajectory section. Returns trend."""
    print("\nTECH DEBT TRAJECTORY")
    print("-" * 40)

    trend = wc._get_tech_debt_trend(patterns_dir)
    print(_TREND_MESSAGES.get(trend, "  Unknown"))

    tech_debt_file = Path(patterns_dir) / "tech_debt.json"
    if tech_debt_file.exists():
        try:
            validated_debt_path = _validate_file_path(str(tech_debt_file))
            with open(validated_debt_path) as f:
                data = json.load(f)
            snapshots = data.get("snapshots", [])
            if snapshots:
                hotspots = snapshots[-1].get("hotspots", [])[:3]
                if hotspots:
                    print("\n  Top hotspots:")
                    for hotspot in hotspots:
                        print(f"    - {hotspot}")
        except (OSError, json.JSONDecodeError):
            pass

    return trend


def _print_health_check(wc: Any, project_root: str) -> None:
    """Print the quick health check section."""
    print("\nQUICK HEALTH CHECK")
    print("-" * 40)

    checks_passed = 0
    checks_total = 2

    success, output = wc._run_command(["ruff", "check", project_root, "--statistics", "-q"])
    if success:
        checks_passed += 1
        print("  Lint:     OK")
    else:
        issues = sum(1 for line in output.split("\n") if line.strip())
        print(f"  Lint:     {issues} issues")

    success, output = wc._run_command(["git", "status", "--porcelain"])
    if success:
        changes = sum(1 for line in output.split("\n") if line.strip())
        if changes == 0:
            checks_passed += 1
            print("  Git:      Clean")
        else:
            print(f"  Git:      {changes} uncommitted files")

    print(f"\n  Overall:  {checks_passed}/{checks_total} checks passed")


def morning_workflow(
    patterns_dir: str = "./patterns",
    project_root: str = ".",
    verbose: bool = False,
) -> int:
    """Start-of-day developer briefing.

    Returns exit code (0 = success).
    """
    wc = _wc()
    print("\n" + "=" * 60)
    print("  MORNING BRIEFING")
    print("  " + datetime.now().strftime("%A, %B %d, %Y"))
    print("=" * 60 + "\n")

    stats = wc._load_stats()
    patterns = wc._load_patterns(patterns_dir)

    total_bugs = _print_patterns_section(patterns)
    trend = _print_tech_debt_section(wc, patterns_dir)
    _print_health_check(wc, project_root)

    # Suggested focus
    print("\nSUGGESTED FOCUS TODAY")
    print("-" * 40)

    suggestions = []
    investigating = [p for p in patterns.get("debugging", []) if p.get("status") == "investigating"]
    if investigating:
        suggestions.append(
            f"Resolve {len(investigating)} investigating bug(s)"
            " via 'attune workflow run bug-predict'",
        )
    if trend == "increasing":
        suggestions.append("Address tech debt - run 'attune doctor' for priorities")
    if total_bugs == 0:
        suggestions.append("Start learning patterns - run 'attune workflow run code-review'")
    if not suggestions:
        suggestions.append("Ship something great! Run 'attune workflow run ship' before committing")

    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"  {i}. {suggestion}")

    stats["last_session"] = datetime.now().isoformat()
    stats["commands"]["morning"] = stats["commands"].get("morning", 0) + 1
    wc._save_stats(stats)

    print("\n" + "=" * 60)
    print("  Have a productive day!")
    print("=" * 60 + "\n")

    return 0


def cmd_morning(args: object) -> int:
    """Morning briefing command handler."""
    return _wc().morning_workflow(
        patterns_dir=getattr(args, "patterns_dir", "./patterns"),
        project_root=getattr(args, "project_root", "."),
        verbose=getattr(args, "verbose", False),
    )
