"""Tests for ``scripts/ledger_precision.py`` — the R5 ledger precision tally.

Each disposition shape the classifier discriminates is pinned as a
fixture (the discriminators are the fragile part — see the calibration
lesson in ``.claude/lessons.md``), and the real ledger is tallied with
a shrink-only ratchet on unclassified review rows: a new row must use
the vocabulary or the tally stops being mechanical.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ledger_precision.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("_ledger_precision", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    sys.modules["_ledger_precision"] = m
    spec.loader.exec_module(m)
    return m


def _row(seat: str, findings: str, disposition: str, date: str = "2026-08-23") -> str:
    return f"| {date} | {seat} | target | 1 sent / 0 omitted | {findings} | {disposition} |"


@pytest.mark.parametrize(
    ("findings", "disposition", "expected"),
    [
        ("0 (clean)", "clean", (0, 0)),
        ("0 (clean)", "clean — NO FINDINGS from the seat [P1]", (0, 0)),
        ("1 (findings)", "real — accepted and fixed in-branch (high: x)", (1, 0)),
        ("3 (findings)", "all real — accepted and fixed in-branch", (3, 0)),
        ("2 (findings)", "both real — accepted and fixed in-branch", (2, 0)),
        ("1 (findings)", "real, severity DOWNGRADED high → low — accepted", (1, 0)),
        ("5 (findings)", "4 real — accepted and fixed in-branch (high: y)", (4, 1)),
        ("7 (findings)", "5 real accepted + fixed in-branch", (5, 2)),
        ("2 (findings)", "one real, one rejected. REAL — accepted", (1, 1)),
        ("1 (findings)", 'dismissed — claim: "x" — reason: y', (0, 1)),
        ("1 (findings)", 'rejected — claim: "x" — reason: y', (0, 1)),
        ("1 (findings)", 'rejected-as-stated, alignment adopted — claim: "x" — reason: y', (0, 1)),
        ("1 (findings)", 'noise-as-stated, readability adopted — claim: "x" — reason: y', (0, 1)),
        # Findings count contradicts the disposition (cross-review on
        # #2206): surfaced as unclassified, never a negative remainder.
        ("5 (findings)", "clean", (None, None)),
        ("2 (findings)", "5 real — accepted and fixed in-branch", (None, None)),
        # Not a review verdict: left for a human, never guessed.
        ("5 (findings)", "ruled at the #1559 lift (row closed 2026-07-30)", (None, None)),
        ("3 (findings)", "stale-branch — carry only if revived", (None, None)),
        ("2 lead amendments", "lead-integrated with recorded amendments", (None, None)),
    ],
)
def test_classify_each_disposition_shape(mod, findings, disposition, expected):
    rows = mod.parse_rows(_row("codex", findings, disposition))
    assert len(rows) == 1
    assert (rows[0].real, rows[0].rejected) == expected


def test_tally_sums_per_seat_and_names_unclassified(mod):
    text = "\n".join(
        [
            "| Date | Seat | Target | Files | Findings | Disposition |",
            "|---|---|---|---|---|---|",
            _row("codex", "0 (clean)", "clean"),
            _row("codex", "4 (findings)", "3 real — accepted and fixed in-branch"),
            _row("codex", "1 (findings)", 'rejected — claim: "x" — reason: y'),
            _row("codex", "3 (findings)", "stale-branch — carry only if revived"),
            _row("antigravity", "2 (findings)", "both real — accepted"),
            _row("codex (implements)", "0 lead amendments", "lead-integrated clean"),
        ]
    )
    seats = mod.tally(mod.parse_rows(text))

    codex = seats["codex"]
    assert (codex.lanes, codex.clean, codex.sent) == (4, 1, 5)
    assert (codex.real, codex.rejected) == (3, 2)
    assert codex.precision == 0.6
    assert len(codex.unclassified) == 1 and "stale-branch" in codex.unclassified[0]

    assert seats["antigravity"].precision == 1.0
    assert "codex (implements)" not in seats  # implement lanes are not review lanes


def test_tool_notes_tally_inline_bug_predict_precision(mod):
    text = (
        "| 2026-08-23 | codex | t | 3 sent / 0 omitted | 1 (findings) | real — fixed. "
        "Ledger precision note: bug-predict's 3 reported findings on this file were 3 real; "
        "the seat's 1 was 1 real [P1] |\n"
        "| 2026-08-24 | codex | t | 1 sent / 0 omitted | 0 (clean) | clean — "
        "bug-predict's 7 reported findings were 3 real |\n"
    )
    tools = mod.tool_notes(text)
    bp = tools["bug-predict"]
    assert (bp.lanes, bp.sent, bp.real, bp.rejected) == (2, 10, 6, 4)
    assert bp.precision == 0.6


def test_precision_is_none_with_nothing_judged(mod):
    t = mod.SeatTally(lanes=1, clean=1)
    assert t.precision is None
    assert "n/a" in mod.render({"codex": t}, {})


def test_cli_json_on_the_real_ledger(mod, capsys):
    assert mod.main(["--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["seats"]["codex"]["sent"] > 0
    assert payload["seats"]["codex"]["precision"] is not None


#: Review-lane rows the classifier cannot read, as of 2026-08-23. Shrink
#: only: a NEW unclassified row means a disposition written outside the
#: vocabulary, and the tally silently stops being "yield measured".
KNOWN_UNCLASSIFIED = frozenset(
    {
        "2026-07-29: ruled at the #1559 lift",
        "2026-07-29: stale-branch — carry only if revived",
        "2026-08-20: Manifest was PARTIAL",
    }
)


def test_real_ledger_has_no_new_unclassified_review_rows(mod):
    seats = mod.tally(mod.parse_rows(mod.LEDGER.read_text(encoding="utf-8")))
    unclassified = [u for t in seats.values() for u in t.unclassified]
    new = [u for u in unclassified if not any(u.startswith(k) for k in KNOWN_UNCLASSIFIED)]
    assert not new, (
        "R5 ledger review rows whose disposition the precision tally cannot read "
        f"(start with clean / real / N real / dismissed|noise|rejected): {new}"
    )
    gone = [k for k in KNOWN_UNCLASSIFIED if not any(u.startswith(k) for u in unclassified)]
    assert not gone, f"KNOWN_UNCLASSIFIED entries no longer in the ledger — shrink the set: {gone}"


def test_absent_lane_rows_are_kept_in_the_ledger_but_skipped_by_the_tally(mod):
    # ``review.ledger_row`` writes an ABSENT lane (seat never read the brief)
    # as ``0 (absent)``. It is a real run the ledger keeps, but it judged
    # nothing: it must count neither as clean nor as unreadable.
    text = "\n".join(
        [
            _row("codex", "0 (absent)", "ABSENT — CLI exited 1 before reading the brief"),
            _row("antigravity", "2 (findings)", "2 real — fixed"),
        ]
    )
    rows = mod.parse_rows(text)
    assert [r.seat for r in rows] == ["antigravity"]
    seats = mod.tally(rows)
    assert "codex" not in seats
    assert not [u for t in seats.values() for u in t.unclassified]
