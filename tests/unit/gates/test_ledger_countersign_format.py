"""D11c guard: countersign claims in the R5 ledger are citable.

The lead's central receipt re-runs are countersigned by a non-lead
skeptic seat from an executor-produced, digest-verified artifact
(feature-lead-governance D11c, 2026-07-29). A ledger row that claims
a countersign (or a dissent) must carry the full citable token —
seat, cited receipt label, and artifact digest — so the chair can
audit the named artifact instead of trusting the lead's word:

    countersign: <seat> :: <label> :: sha256:<16+ hex>
    dissent: <seat> :: <label> :: sha256:<16+ hex>

The grammar is IMPORTED from the producing module
(:data:`attune.roundtable.countersign.COUNTERSIGN_TOKEN_RE`) — one
source, so the gate and the token formatter cannot drift apart. A
bare "countersign:" without the artifact digest is exactly the
lead-narrated claim D11c exists to reject; this gate fails on it.
"""

from __future__ import annotations

import re
from pathlib import Path

from attune.roundtable.countersign import COUNTERSIGN_TOKEN_RE

REPO_ROOT = Path(__file__).parents[3]
LEDGER = REPO_ROOT / "docs/specs/cross-review/receipts.md"

_CLAIM = re.compile(r"\b(?:countersign|dissent):", re.IGNORECASE)


def _ledger_rows() -> list[str]:
    rows = [
        line
        for line in LEDGER.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| \d{4}-\d{2}-\d{2} \|", line)
    ]
    assert rows, f"no ledger rows found in {LEDGER} — table format changed?"
    return rows


def _uncited_claims(row: str) -> list[str]:
    """Claim markers in the row not covered by a full citable token."""
    stripped = COUNTERSIGN_TOKEN_RE.sub("", row)
    return [m.group(0) for m in _CLAIM.finditer(stripped)]


def test_countersign_claims_carry_full_token():
    bad = [row for row in _ledger_rows() if _uncited_claims(row)]
    assert not bad, (
        "R5 ledger rows claim a countersign/dissent without the citable "
        "token 'countersign: <seat> :: <label> :: sha256:<hex>' "
        f"(D11c): {bad}"
    )


def test_gate_fires_on_bare_claim():
    # Fires-on-violation receipt: a lead-narrated claim without the
    # artifact digest must be caught, a full token must pass.
    bare = "| 2026-07-29 | codex | t | 1 | 1 | real — countersigned by codex |"
    assert not _uncited_claims(bare)  # 'countersigned by' is prose, not a claim marker
    claim = "| 2026-07-29 | codex | t | 1 | 1 | real — countersign: codex said fine |"
    assert _uncited_claims(claim)
    full = (
        "| 2026-07-29 | codex | t | 1 | 1 | real — "
        "countersign: antigravity :: unit-suite :: sha256:0123456789abcdef |"
    )
    assert not _uncited_claims(full)
