#!/usr/bin/env python3
"""Real-time agent monitoring.

Monitors background agent task outputs and provides JSON status updates
that can be viewed in terminal.

Usage:
    python scripts/monitor_agents.py                    # Watch mode (updates every 2s)
    python scripts/monitor_agents.py --once              # Single snapshot
    python scripts/monitor_agents.py --json              # JSON output only
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

AGENT_OUTPUT_DIR = Path("/private/tmp/claude/-Users-example-attune-ai/tasks/")


def parse_agent_output(output_file: Path) -> Dict[str, Any]:
    """Parse agent output file to extract progress metrics."""
    if not output_file.exists():
        return {
            "status": "not_found",
            "modules_completed": 0,
            "tests_added": 0,
            "errors": 0,
        }

    try:
        content = output_file.read_text()

        # Extract metrics from agent output
        modules_completed = len(re.findall(r"✅.*?test_\w+_behavioral\.py", content))
        tests_pattern = r"(\d+)\s+tests?\s+added"
        tests_matches = re.findall(tests_pattern, content)
        tests_added = sum(int(m) for m in tests_matches) if tests_matches else 0

        errors = len(re.findall(r"❌|ERROR|FAILED", content))

        # Determine status
        if "COMPLETED" in content or "Summary Report" in content:
            status = "completed"
        elif modules_completed > 0 or tests_added > 0:
            status = "in_progress"
        elif errors > 0:
            status = "error"
        else:
            status = "running"

        # Get last update time
        last_modified = datetime.fromtimestamp(output_file.stat().st_mtime)

        # Extract batch info from content
        batch_match = re.search(r"Batch (\d+):", content)
        batch_num = int(batch_match.group(1)) if batch_match else None

        focus_match = re.search(r"(?:Batch \d+:|Agent Batch \d+:)\s*(.+?)(?:\n|$)", content)
        focus_area = focus_match.group(1).strip() if focus_match else "Unknown"

        return {
            "status": status,
            "modules_completed": modules_completed,
            "tests_added": tests_added,
            "errors": errors,
            "last_update": last_modified.isoformat(),
            "batch_num": batch_num,
            "focus_area": focus_area,
            "output_size_kb": output_file.stat().st_size / 1024,
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": str(e),
            "modules_completed": 0,
            "tests_added": 0,
            "errors": 1,
        }


def get_all_agent_status() -> Dict[str, Any]:
    """Get status of all running agents."""
    if not AGENT_OUTPUT_DIR.exists():
        return {
            "timestamp": datetime.now().isoformat(),
            "total_agents": 0,
            "agents": {},
            "summary": {
                "running": 0,
                "completed": 0,
                "error": 0,
                "total_modules": 0,
                "total_tests": 0,
                "total_errors": 0,
            },
        }

    agents = {}
    summary = {
        "running": 0,
        "in_progress": 0,
        "completed": 0,
        "error": 0,
        "total_modules": 0,
        "total_tests": 0,
        "total_errors": 0,
    }

    # Find all agent output files
    for output_file in sorted(AGENT_OUTPUT_DIR.glob("*.output")):
        agent_id = output_file.stem
        status = parse_agent_output(output_file)
        agents[agent_id] = status

        # Update summary
        if status["status"] == "completed":
            summary["completed"] += 1
        elif status["status"] == "in_progress":
            summary["in_progress"] += 1
        elif status["status"] == "error":
            summary["error"] += 1
        else:
            summary["running"] += 1

        summary["total_modules"] += status.get("modules_completed", 0)
        summary["total_tests"] += status.get("tests_added", 0)
        summary["total_errors"] += status.get("errors", 0)

    return {
        "timestamp": datetime.now().isoformat(),
        "total_agents": len(agents),
        "agents": agents,
        "summary": summary,
    }


def print_dashboard_view(status: Dict[str, Any]):
    """Print human-readable status view."""
    print("\n" + "=" * 80)
    print("🤖  AGENT MONITORING")
    print("=" * 80)
    print(f"Timestamp: {status['timestamp']}")
    print(f"Total Agents: {status['total_agents']}")
    print()

    summary = status["summary"]
    print("📊 Summary:")
    print(f"  Running:      {summary['running'] + summary['in_progress']}")
    print(f"  Completed:    {summary['completed']}")
    print(f"  Errors:       {summary['error']}")
    print(f"  Total Modules: {summary['total_modules']}")
    print(f"  Total Tests:   {summary['total_tests']}")
    print()

    if status["agents"]:
        print("🔍 Agent Details:")
        for agent_id, agent_status in sorted(status["agents"].items()):
            status_icon = {
                "completed": "✅",
                "in_progress": "🔄",
                "running": "🟢",
                "error": "❌",
                "not_found": "⚪",
            }.get(agent_status["status"], "❓")

            batch_info = (
                f"Batch {agent_status.get('batch_num', '?')}"
                if agent_status.get("batch_num")
                else ""
            )
            focus = agent_status.get("focus_area", "Unknown")

            print(
                f"  {status_icon} {agent_id[:8]}... | {batch_info:8} | {focus[:30]:30} | "
                f"Modules: {agent_status['modules_completed']:2} | Tests: {agent_status['tests_added']:3}"
            )

    print("=" * 80)
    print()


def main():
    """Main monitoring loop."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor agent progress")
    parser.add_argument("--once", action="store_true", help="Single snapshot (no watch)")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--interval", type=int, default=2, help="Update interval in seconds")

    args = parser.parse_args()

    try:
        while True:
            status = get_all_agent_status()

            if args.json:
                print(json.dumps(status, indent=2))
            else:
                print_dashboard_view(status)

            if args.once:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
