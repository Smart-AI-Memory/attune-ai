#!/usr/bin/env python3
"""Per-source precision tally over the R5 cross-review ledger.

The feature-lead-governance ruling (chair, 2026-07-30) keeps risk-
triggered review lanes as the permanent default on the condition that
"yield stays measured in the R5 ledger". Until now that measurement was
a human reading 90 prose rows. This script makes it mechanical: it
parses ``docs/specs/cross-review/receipts.md`` and reports, per review
seat, how many findings were sent and how many the lead accepted as
real versus rejected — the seat's precision — plus the same tally for
any tool whose precision a row records inline (today: bug-predict).

Rows are classified from the disposition cell's leading shape, which
the ledger has kept stable since D11a:

* ``clean …``                          -> 0 findings, 0 real
* ``real …`` / ``all real`` / ``both real`` -> every finding real
* ``N real …`` / ``one real, one rejected`` -> N real, rest rejected
* ``dismissed`` / ``noise`` / ``rejected`` (incl. ``-as-stated``) -> all rejected

Anything else (implement lanes, delegated coverage lanes, chair-ruled
or parked rows) is reported as UNCLASSIFIED, never silently dropped.

Usage::

    python scripts/ledger_precision.py           # table to stdout
    python scripts/ledger_precision.py --json    # machine-readable

Exit code is always 0 — this is a report, not a gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER = REPO_ROOT / "docs/specs/cross-review/receipts.md"

#: Seats whose rows are review lanes (others are implement/coverage lanes).
REVIEW_SEATS = ("codex", "antigravity")

_ROW = re.compile(r"^\| \d{4}-\d{2}-\d{2} \|")
_FINDINGS = re.compile(r"^(\d+) \((findings|clean)")
_REJECTION = re.compile(r"^(?:dismissed|noise|rejected)\b")
_ALL_REAL = re.compile(r"^(?:all |both )?real\b")
_N_REAL = re.compile(r"^(\d+|one|two|three|four|five) real\b")
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
#: Inline precision notes, e.g. "bug-predict's 3 reported findings on
#: this file were 3 real".
_TOOL_NOTE = re.compile(r"(bug-predict)'s (\d+) reported findings[^.;]*?\b(\d+) real")


@dataclass
class Row:
    date: str
    seat: str
    findings: int | None  # None when the Findings cell is not "N (findings|clean)"
    real: int | None
    rejected: int | None
    disposition: str

    @property
    def classified(self) -> bool:
        return self.real is not None


@dataclass
class SeatTally:
    lanes: int = 0
    clean: int = 0
    sent: int = 0
    real: int = 0
    rejected: int = 0
    unclassified: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        judged = self.real + self.rejected
        return round(self.real / judged, 3) if judged else None


def classify(findings: int | None, disposition: str) -> tuple[int | None, int | None]:
    """Return ``(real, rejected)`` for one row, or ``(None, None)`` when the
    disposition shape is not one the tally knows."""
    d = disposition.strip()
    if findings is None:
        return None, None
    # A row whose Findings count contradicts its disposition is NOT
    # guessed at: "5 (findings) | clean" or "2 (findings) | 5 real" is
    # a ledger error to surface, not a negative rejection count.
    if d.lower().startswith("clean"):
        return (0, 0) if findings == 0 else (None, None)
    if _REJECTION.match(d):
        return 0, findings
    m = _N_REAL.match(d)
    if m:
        real = _WORDS.get(m.group(1)) or int(m.group(1))
        return (real, findings - real) if real <= findings else (None, None)
    if _ALL_REAL.match(d):
        return findings, 0
    return None, None


def parse_rows(text: str) -> list[Row]:
    rows: list[Row] = []
    for line in text.splitlines():
        if not _ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        date, seat, _target, _files, findings_cell, disposition = cells[:6]
        m = _FINDINGS.match(findings_cell)
        findings = int(m.group(1)) if m else None
        real, rejected = classify(findings, disposition)
        rows.append(Row(date, seat, findings, real, rejected, disposition))
    return rows


def tally(rows: list[Row]) -> dict[str, SeatTally]:
    out: dict[str, SeatTally] = {}
    for row in rows:
        if row.seat not in REVIEW_SEATS:
            continue
        t = out.setdefault(row.seat, SeatTally())
        t.lanes += 1
        if not row.classified:
            t.unclassified.append(f"{row.date}: {row.disposition[:60]}")
            continue
        if row.findings == 0:
            t.clean += 1
        t.sent += row.findings or 0
        t.real += row.real or 0
        t.rejected += row.rejected or 0
    return out


def tool_notes(text: str) -> dict[str, SeatTally]:
    """Precision recorded inline for tools (not seats), e.g. bug-predict."""
    out: dict[str, SeatTally] = {}
    for tool, reported, real in _TOOL_NOTE.findall(text):
        t = out.setdefault(tool, SeatTally())
        t.lanes += 1
        t.sent += int(reported)
        t.real += int(real)
        t.rejected += int(reported) - int(real)
    return out


def render(seats: dict[str, SeatTally], tools: dict[str, SeatTally]) -> str:
    lines = [
        "| Source | Lanes | Clean | Sent | Real | Rejected | Precision |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, t in [*seats.items(), *tools.items()]:
        p = "n/a" if t.precision is None else f"{t.precision:.0%}"
        lines.append(
            f"| {name} | {t.lanes} | {t.clean} | {t.sent} | {t.real} | {t.rejected} | {p} |"
        )
    for name, t in seats.items():
        if t.unclassified:
            lines.append("")
            lines.append(f"{name}: {len(t.unclassified)} unclassified row(s) (read by hand):")
            lines.extend(f"  - {u}" for u in t.unclassified)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", type=Path, default=LEDGER)
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args(argv)

    text = args.ledger.read_text(encoding="utf-8")
    seats = tally(parse_rows(text))
    tools = tool_notes(text)
    if args.json:
        payload = {
            "seats": {k: {**asdict(v), "precision": v.precision} for k, v in seats.items()},
            "tools": {k: {**asdict(v), "precision": v.precision} for k, v in tools.items()},
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render(seats, tools))
    return 0


if __name__ == "__main__":
    sys.exit(main())
