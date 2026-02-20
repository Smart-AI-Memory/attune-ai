"""Morning Briefing Workflow for Attune AI.

Start-of-day developer briefing with patterns, debt, and focus areas.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path


def _wc():
    """Late-resolve the workflow_commands facade for patchable helper access."""
    return sys.modules["attune.workflow_commands"]


def morning_workflow(
    patterns_dir: str = "./patterns",
    project_root: str = ".",
    verbose: bool = False,
) -> int:
    """Start-of-day developer briefing.

    Shows:
    - Health check summary
    - Patterns learned since last session
    - Tech debt trajectory
    - Suggested focus areas

    Returns exit code (0 = success).
    """
    wc = _wc()
    print("\n" + "=" * 60)
    print("  MORNING BRIEFING")
    print("  " + datetime.now().strftime("%A, %B %d, %Y"))
    print("=" * 60 + "\n")

    # Load stats and patterns
    stats = wc._load_stats()
    patterns = wc._load_patterns(patterns_dir)

    # 1. Patterns summary
    print("PATTERNS LEARNED")
    print("-" * 40)

    total_bugs = len(patterns.get("debugging", []))
    resolved_bugs = sum(1 for p in patterns.get("debugging", []) if p.get("status") == "resolved")
    security_decisions = len(patterns.get("security", []))

    print(f"  Bug patterns:        {total_bugs} ({resolved_bugs} resolved)")
    print(f"  Security decisions:  {security_decisions}")
    print(f"  Inspection patterns: {len(patterns.get('inspection', []))}")

    # Recent patterns (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_bugs = []
    for bug in patterns.get("debugging", []):
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

    # 2. Tech debt trajectory
    print("\n" + "TECH DEBT TRAJECTORY")
    print("-" * 40)

    trend = wc._get_tech_debt_trend(patterns_dir)
    trend_icons = {
        "increasing": "  Trending UP - Consider allocating time for cleanup",
        "decreasing": "  Trending DOWN - Great progress!",
        "stable": "  Stable - Holding steady",
        "unknown": "  Run 'empathy inspect' to start tracking",
        "insufficient_data": "  Not enough data yet - keep coding!",
    }
    print(trend_icons.get(trend, "  Unknown"))

    # Show hotspots if available
    tech_debt_file = Path(patterns_dir) / "tech_debt.json"
    if tech_debt_file.exists():
        try:
            with open(tech_debt_file) as f:
                data = json.load(f)
            snapshots = data.get("snapshots", [])
            if snapshots:
                latest = snapshots[-1]
                hotspots = latest.get("hotspots", [])[:3]
                if hotspots:
                    print("\n  Top hotspots:")
                    for hotspot in hotspots:
                        print(f"    - {hotspot}")
        except (OSError, json.JSONDecodeError):
            pass

    # 3. Quick health check
    print("\n" + "QUICK HEALTH CHECK")
    print("-" * 40)

    checks_passed = 0
    checks_total = 0

    # Check for ruff
    checks_total += 1
    success, output = wc._run_command(["ruff", "check", project_root, "--statistics", "-q"])
    if success:
        checks_passed += 1
        print("  Lint:     OK")
    else:
        issues = sum(1 for line in output.split("\n") if line.strip())
        print(f"  Lint:     {issues} issues")

    # Check for uncommitted changes
    checks_total += 1
    success, output = wc._run_command(["git", "status", "--porcelain"])
    if success:
        changes = sum(1 for line in output.split("\n") if line.strip())
        if changes == 0:
            checks_passed += 1
            print("  Git:      Clean")
        else:
            print(f"  Git:      {changes} uncommitted files")

    print(f"\n  Overall:  {checks_passed}/{checks_total} checks passed")

    # 4. Suggested focus
    print("\n" + "SUGGESTED FOCUS TODAY")
    print("-" * 40)

    suggestions = []

    # Based on patterns
    investigating_bugs = [
        p for p in patterns.get("debugging", []) if p.get("status") == "investigating"
    ]
    if investigating_bugs:
        suggestions.append(
            f"Resolve {len(investigating_bugs)} investigating bug(s)"
            " via 'empathy patterns resolve'",
        )

    if trend == "increasing":
        suggestions.append("Address tech debt - run 'empathy status' for priorities")

    if total_bugs == 0:
        suggestions.append("Start learning patterns - run 'empathy learn' or 'empathy inspect'")

    if not suggestions:
        suggestions.append("Ship something great! Run 'empathy ship' before committing")

    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"  {i}. {suggestion}")

    # Update stats
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
