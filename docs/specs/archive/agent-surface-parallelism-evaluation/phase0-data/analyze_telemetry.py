#!/usr/bin/env python3
"""Phase 0.1 analysis for agent-surface-parallelism-evaluation spec.

Computes the headline frequency metric the pre-committed decision matrix
needs: % of sessions invoking >= 2 analytical workflows.

Inputs:
    ~/.attune/telemetry/usage.jsonl (v1.0 schema)

Outputs (written next to this script):
    multi-workflow-sessions.csv — one row per inferred session
    summary.txt — headline metrics and distributions

Session inference: time-gap heuristic per user_id; a gap > 30 minutes
between consecutive events starts a new session. Test fixture workflows
(stub-workflow, test-tier-fallback, test-workflow, success-workflow,
failing-stub) are excluded.

Analytical workflows are the user-facing review/audit family the spec
proposes to fan out: security-audit, code-review, bug-predict,
deep-review, refactor-plan, perf-audit, test-audit, doc-audit.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

USAGE = Path.home() / ".attune/telemetry/usage.jsonl"
OUT_DIR = Path(__file__).resolve().parent

TEST_WORKFLOWS = {
    "stub-workflow",
    "test-tier-fallback",
    "test-workflow",
    "success-workflow",
    "failing-stub",
}

ANALYTICAL = {
    "security-audit",
    "code-review",
    "bug-predict",
    "deep-review",
    "refactor-plan",
    "perf-audit",
    "test-audit",
    "doc-audit",
}

SESSION_GAP = timedelta(minutes=30)


def load_events() -> list[tuple[str, datetime, str]]:
    events: list[tuple[str, datetime, str]] = []
    with USAGE.open() as f:
        for line in f:
            d = json.loads(line)
            wf = d.get("workflow", "")
            if wf in TEST_WORKFLOWS:
                continue
            ts = datetime.fromisoformat(d["ts"].replace("Z", "+00:00"))
            events.append((d["user_id"], ts, wf))
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def infer_sessions(events: list[tuple[str, datetime, str]]) -> list[dict]:
    sessions: list[dict] = []
    current: dict | None = None
    for uid, ts, wf in events:
        if current is None or current["user_id"] != uid or (ts - current["last_ts"]) > SESSION_GAP:
            if current is not None:
                sessions.append(current)
            current = {
                "user_id": uid,
                "start": ts,
                "last_ts": ts,
                "workflows": set(),
                "ordered_workflows": [],
                "events": 0,
            }
        current["last_ts"] = ts
        current["workflows"].add(wf)
        if not current["ordered_workflows"] or current["ordered_workflows"][-1] != wf:
            current["ordered_workflows"].append(wf)
        current["events"] += 1
    if current is not None:
        sessions.append(current)
    return sessions


def main() -> None:
    events = load_events()
    sessions = infer_sessions(events)

    # CSV — one row per session
    csv_path = OUT_DIR / "multi-workflow-sessions.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "session_idx",
                "user_id_hash",
                "start_utc",
                "duration_min",
                "event_count",
                "distinct_workflows",
                "analytical_workflows",
                "workflows_invoked",
            ]
        )
        for i, s in enumerate(sessions, 1):
            duration_min = (s["last_ts"] - s["start"]).total_seconds() / 60.0
            analytical = sorted(w for w in s["workflows"] if w in ANALYTICAL)
            w.writerow(
                [
                    i,
                    s["user_id"][:8],
                    s["start"].isoformat(),
                    f"{duration_min:.1f}",
                    s["events"],
                    len(s["workflows"]),
                    len(analytical),
                    " ".join(s["ordered_workflows"]),
                ]
            )

    # Summary
    total = len(sessions)
    multi_wf = sum(1 for s in sessions if len(s["workflows"]) >= 2)
    multi_analytical = sum(
        1 for s in sessions if sum(1 for w in s["workflows"] if w in ANALYTICAL) >= 2
    )
    pure_analytical = sum(1 for s in sessions if any(w in ANALYTICAL for w in s["workflows"]))

    pct_multi_wf = 100 * multi_wf / total if total else 0
    pct_multi_analytical = 100 * multi_analytical / total if total else 0
    pct_pure_analytical = 100 * pure_analytical / total if total else 0

    wf_count_dist = Counter(len(s["workflows"]) for s in sessions)
    analyt_count_dist = Counter(sum(1 for w in s["workflows"] if w in ANALYTICAL) for s in sessions)

    combo_counter: Counter[tuple[str, ...]] = Counter()
    for s in sessions:
        analytical = tuple(sorted(w for w in s["workflows"] if w in ANALYTICAL))
        if len(analytical) >= 2:
            combo_counter[analytical] += 1

    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("Phase 0.1 — Telemetry Summary")
    lines.append("Spec: agent-surface-parallelism-evaluation")
    lines.append("=" * 60)
    lines.append("")
    if events:
        lines.append(f"Event source: {USAGE}")
        lines.append(f"Date range:   {events[0][1].date()} -> {events[-1][1].date()}")
        lines.append(f"Real events:  {len(events):,} (test fixtures excluded)")
    lines.append(f"Inferred sessions: {total} (30-min idle gap per user_id)")
    lines.append("")
    lines.append("=== HEADLINE METRICS ===")
    lines.append(
        f"Sessions with >=2 distinct workflows (any):      " f"{multi_wf:4d} ({pct_multi_wf:.1f}%)"
    )
    lines.append(
        f"Sessions with >=2 analytical workflows:          "
        f"{multi_analytical:4d} ({pct_multi_analytical:.1f}%)"
    )
    lines.append(
        f"Sessions with >=1 analytical workflow:           "
        f"{pure_analytical:4d} ({pct_pure_analytical:.1f}%)"
    )
    lines.append("")
    lines.append("=== DISTRIBUTIONS ===")
    lines.append("Sessions by distinct-workflow count:")
    for n in sorted(wf_count_dist):
        c = wf_count_dist[n]
        lines.append(f"  {n} workflows: {c:4d} sessions ({100 * c / total:.1f}%)")
    lines.append("")
    lines.append("Sessions by analytical-workflow count:")
    for n in sorted(analyt_count_dist):
        c = analyt_count_dist[n]
        lines.append(f"  {n} analytical: {c:4d} sessions ({100 * c / total:.1f}%)")
    lines.append("")
    lines.append("=== TOP MULTI-ANALYTICAL COMBOS ===")
    for combo, c in combo_counter.most_common(10):
        lines.append(f"  {c:3d}x  {' + '.join(combo)}")
    lines.append("")
    lines.append("Matrix gate (frequency only):")
    if pct_multi_analytical >= 10:
        lines.append(
            f"  PASS  ({pct_multi_analytical:.1f}% >= 10%) — Phase 0.3-0.5 needed "
            f"for wall-clock + qualitative gates"
        )
    elif pct_multi_analytical >= 5:
        lines.append(
            f"  DEFER region  ({pct_multi_analytical:.1f}% in 5-10%) — small "
            f"audience; revisit when telemetry has more data"
        )
    else:
        lines.append(
            f"  RETIRE  ({pct_multi_analytical:.1f}% < 5%) — rare pattern, "
            f"solving a nonexistent problem"
        )

    summary_path = OUT_DIR / "summary.txt"
    summary_path.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print()
    print(f"CSV:     {csv_path}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
