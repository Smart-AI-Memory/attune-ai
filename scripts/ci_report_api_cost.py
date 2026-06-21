#!/usr/bin/env python3
"""Summarize a CI run's API spend from attune telemetry.

Reads the local `~/.attune/telemetry/usage.jsonl` that attune writes on
every tracked LLM call (the runner is ephemeral, so the file holds only
this run's entries) and appends a one-line cost total to the GitHub job
summary (`$GITHUB_STEP_SUMMARY`). Reusable across the paid scheduled
jobs (integration-auth, help-freshness regen).

Note: this reflects spend attune's UsageTracker captured (workflow SDK
calls). Direct-provider test calls that bypass the tracker are not
counted, so treat the figure as a floor, not an exact invoice.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def main() -> int:
    """Sum telemetry cost and write a markdown line to the job summary."""
    telemetry = Path("~/.attune/telemetry/usage.jsonl").expanduser()
    total = 0.0
    calls = 0

    if telemetry.exists():
        for raw in telemetry.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                total += float(json.loads(raw).get("cost", 0.0) or 0.0)
                calls += 1
            except (ValueError, json.JSONDecodeError):
                continue
        body = (
            f"## API cost this run\n\n"
            f"**${total:.4f}** across {calls} telemetry-tracked LLM "
            f"call(s).\n\n"
            f"_Floor estimate — direct-provider calls that bypass "
            f"UsageTracker are not counted._\n"
        )
    else:
        body = (
            "## API cost this run\n\n"
            "No telemetry written — likely an auth/setup failure before "
            "any billable call.\n"
        )

    print(body)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
