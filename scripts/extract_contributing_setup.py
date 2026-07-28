#!/usr/bin/env python3
"""Extract CONTRIBUTING.md's literal setup commands for the G4(c) lane.

The CONTRIBUTING clean-venv CI lane (claim-drift-gates G4c, D6)
executes the setup commands a new contributor actually reads —
extracted from the doc AT RUN TIME, so the lane can never drift from
the doc it guards. Hardcoding the commands in the workflow would
itself be a claim-drift surface.

Extraction contract:

- The FIRST ``bash`` fence after the ``### Setup Development
  Environment`` heading is the setup script.
- ``git clone`` / ``cd attune-ai`` lines are commented out — CI
  already runs inside the checkout under test (a literal clone would
  test ``main``, not the PR).
- A bare ``pytest tests/`` verification line gets the G4(c) subset
  arguments appended (``-x -k smoke`` — keyless CI runs the smoke
  subset, not the full suite).

Every other line is executed VERBATIM under ``bash -euo pipefail``.

Usage:

    python scripts/extract_contributing_setup.py            # print script
    python scripts/extract_contributing_setup.py --check    # validate only

Exit codes: 0 ok; 1 the doc no longer matches the extraction
contract (heading or fence missing, no pytest line) — the lane fails
loudly instead of silently testing nothing.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEADING = "### Setup Development Environment"
_FENCE_RE = re.compile(r"```bash\s*\n(.*?)```", re.DOTALL)

#: Appended to the doc's bare ``pytest tests/`` line (G4c contract).
SMOKE_ARGS = "-x -k smoke"


def extract(text: str) -> str:
    """Return the runnable setup script from CONTRIBUTING text.

    Raises:
        ValueError: When the heading, fence, or pytest line is gone —
            the doc restructured and the lane must fail loudly.
    """
    idx = text.find(HEADING)
    if idx < 0:
        raise ValueError(f"heading {HEADING!r} not found in CONTRIBUTING.md")
    m = _FENCE_RE.search(text, idx)
    if not m:
        raise ValueError(f"no bash fence found after {HEADING!r}")
    lines: list[str] = ["set -euo pipefail", ""]
    saw_pytest = False
    for ln in m.group(1).splitlines():
        stripped = ln.strip()
        if stripped.startswith("git clone ") or stripped == "cd attune-ai":
            lines.append(f"# [g4c: runs in the checkout under test] {ln}")
            continue
        if re.fullmatch(r"pytest\s+tests/?", stripped):
            lines.append(f"{ln} {SMOKE_ARGS}")
            saw_pytest = True
            continue
        lines.append(ln)
    if not saw_pytest:
        raise ValueError(
            "no bare 'pytest tests/' verification line in the setup fence — "
            "update this extractor's contract alongside the doc"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only, print nothing")
    args = parser.parse_args(argv)
    doc = Path(__file__).resolve().parent.parent / "CONTRIBUTING.md"
    try:
        script = extract(doc.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"extract_contributing_setup: {exc}", file=sys.stderr)
        return 1
    if not args.check:
        print(script, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
