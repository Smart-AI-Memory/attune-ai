#!/usr/bin/env python3
"""Summarize help-query telemetry.

Reads ``~/.attune/telemetry/help_queries.jsonl`` and prints a short
report: total queries, query breakdown by source/mode, most-queried
topics, and miss rate (queries that returned no result).

Use this after a couple of weeks of real use to decide which features
deserve corpus investment.

Usage:
    python scripts/summarize_help_telemetry.py
    python scripts/summarize_help_telemetry.py --top 20
    python scripts/summarize_help_telemetry.py --since 2026-04-01
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def _parse_events(path: Path, since: datetime | None) -> list[dict]:
    if not path.is_file():
        return []
    events: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since is not None:
                try:
                    event_ts = datetime.fromisoformat(event["ts"])
                except (KeyError, ValueError):
                    continue
                if event_ts < since:
                    continue
            events.append(event)
    return events


def _render(events: list[dict], top: int) -> str:
    if not events:
        return "no help-query telemetry yet"

    lines = [f"total queries: {len(events)}"]

    sources = Counter(e.get("source", "?") for e in events)
    lines.append(f"by source: {dict(sources)}")

    modes = Counter(e.get("mode", "?") for e in events)
    lines.append(f"by mode: {dict(modes)}")

    misses = sum(1 for e in events if not e.get("found"))
    lines.append(f"miss rate: {misses}/{len(events)} ({misses / len(events):.0%})")

    topics = Counter(e.get("topic", "?") for e in events).most_common(top)
    lines.append(f"top {top} topics:")
    for topic, count in topics:
        lines.append(f"  {count:4d}  {topic}")

    miss_topics = Counter(e.get("topic", "?") for e in events if not e.get("found")).most_common(
        top
    )
    if miss_topics:
        lines.append(f"top {top} missed topics (consider corpus investment):")
        for topic, count in miss_topics:
            lines.append(f"  {count:4d}  {topic}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        default=str(Path.home() / ".attune" / "telemetry" / "help_queries.jsonl"),
        help="Path to help_queries.jsonl",
    )
    parser.add_argument("--top", type=int, default=10, help="Top-N topics to list")
    parser.add_argument(
        "--since",
        default=None,
        help="Only include events after this ISO timestamp (e.g. 2026-04-01)",
    )
    args = parser.parse_args()

    since: datetime | None = None
    if args.since:
        try:
            since = datetime.fromisoformat(args.since)
        except ValueError:
            print(f"invalid --since: {args.since!r}", file=sys.stderr)
            return 2

    events = _parse_events(Path(args.path), since)
    print(_render(events, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
