"""D11a guard: rejected findings in the R5 ledger carry the claim verbatim.

The lead dispositions findings about its own diffs — the conflict-of-
interest corner of the lead-verification gap. This guard enforces the
chair-ruled mitigation (feature-lead-governance D11a, 2026-07-29): any
ledger row whose disposition is a rejection class must carry the
reviewing seat's claim VERBATIM plus the lead's reason, so the chair can
spot-check rejections by reading two quoted strings instead of
re-deriving the review:

    <class> — claim: "<seat's words>" — reason: <lead's reason>

Rows predating D11 are explicitly allowlisted below — never silently
exempt. Do not add new rows to the allowlist; new rejections must comply.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
LEDGER = REPO_ROOT / "docs/specs/cross-review/receipts.md"

#: Disposition prefixes that reject a seat's finding (D11a scope).
REJECTION_CLASSES = ("dismissed", "noise", "rejected")

#: Full disposition cells of rows recorded BEFORE the D11 ruling.
PRE_D11_ALLOWLIST = frozenset(
    {
        "dismissed — dated context by design",
    }
)

_COMPLIANT = re.compile(r"^(?:dismissed|noise|rejected)\b[^—]*— claim: \".+\" — reason: .+$")


def _ledger_dispositions() -> list[str]:
    rows = [
        line
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| \d{4}-\d{2}-\d{2} \|", line)
    ]
    assert rows, f"no ledger rows found in {LEDGER} — table format changed?"
    return [line.strip().strip("|").split("|")[-1].strip() for line in rows]


def test_rejection_rows_carry_verbatim_claim_and_reason():
    bad = []
    for disposition in _ledger_dispositions():
        if not disposition.lower().startswith(REJECTION_CLASSES):
            continue
        if disposition in PRE_D11_ALLOWLIST:
            continue
        if not _COMPLIANT.match(disposition):
            bad.append(disposition)
    assert not bad, (
        "R5 ledger rejection rows missing verbatim claim + reason "
        f"(D11a format '<class> — claim: \"...\" — reason: ...'): {bad}"
    )


def test_allowlist_rows_still_exist():
    # A stale allowlist entry means the row was edited or removed — the
    # exemption must shrink with reality, not outlive it.
    dispositions = set(_ledger_dispositions())
    gone = PRE_D11_ALLOWLIST - dispositions
    assert not gone, f"allowlisted pre-D11 rows no longer in the ledger: {gone}"
