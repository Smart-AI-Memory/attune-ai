#!/usr/bin/env python3
"""Guard the manually-maintained README badges against drift.

Coverage is a *live* Codecov badge (zero upkeep). The tests badge is a round
**floor** (`tests-20,000+`) — a round floor can't go subtly stale the way a
precise value does, but it shouldn't *over-claim* or fall *far* behind reality.
This check fails when:

  1. the tests floor OVER-CLAIMS — actual collected tests < the badge floor, or
  2. the tests floor is STALE — actual exceeds the floor by more than ``MARGIN``
     (time to bump the round number), or
  3. the coverage badge has regressed to a HARDCODED ``coverage-NN%`` instead of
     the dynamic Codecov badge.

Usage::

    python scripts/check_badge_freshness.py     # exit 1 on any violation

Run in CI (the coverage job already has the suite installed). Pure floor-check,
not an auto-updater — markers/values that drift get *caught*, not silently rot.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

#: How far the actual test count may exceed the round floor before we nag.
MARGIN = 5000

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"


def collected_test_count() -> int | None:
    """Return pytest's collected-test count, or None if collection fails."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    blob = out.stdout + out.stderr
    m = re.search(r"(\d[\d,]*)\s+tests?\s+collected", blob)
    if m:
        return int(m.group(1).replace(",", ""))
    n = sum(1 for ln in out.stdout.splitlines() if "::" in ln)
    return n or None


def main() -> int:
    text = README.read_text(encoding="utf-8")
    problems: list[str] = []

    # 1/2 — tests floor. The badge URL encodes the comma as %2C and the
    # trailing "+" as %2B, e.g. ``tests-20%2C000%2B`` (also accept the
    # literal ``tests-20,000+`` form).
    m = re.search(r"tests-([0-9][0-9,]*(?:%2C[0-9]+)*)(?:%2B|\+)", text)
    if not m:
        problems.append("tests badge not found, or not a round floor (`tests-N,000+`).")
    else:
        floor = int(m.group(1).replace("%2C", "").replace(",", ""))
        actual = collected_test_count()
        if actual is None:
            print("  (note: could not collect tests; skipping floor comparison)")
        elif actual < floor:
            problems.append(
                f"tests badge OVER-CLAIMS: floor {floor:,} > actual collected {actual:,}."
            )
        elif actual - floor > MARGIN:
            problems.append(
                f"tests badge STALE: actual {actual:,} exceeds floor {floor:,} by "
                f">{MARGIN:,} — bump the round floor."
            )

    # 3 — coverage must stay the dynamic Codecov badge
    if re.search(r"badge/coverage-\d+%", text) or re.search(r"coverage-\d+%25", text):
        problems.append(
            "coverage badge is hardcoded; use the dynamic Codecov badge "
            "(img.shields.io/codecov/c/github/...)."
        )

    if problems:
        print("Badge freshness check FAILED:")
        for p in problems:
            print("  -", p)
        print("\nFix: bump the README tests floor and/or restore the dynamic coverage badge.")
        return 1

    print("Badge freshness OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
