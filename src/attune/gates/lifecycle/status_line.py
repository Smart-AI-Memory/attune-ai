"""Status-line baseline gate (T2, q-briefing-triage-001; n=2 ruled).

Every spec directory must be legible to the lifecycle detector:

- at least one canonical phase file carries a parseable
  ``**Status:**`` line whose leading token is in
  :data:`attune.ops.spec_lifecycle.STATUS_VOCABULARY`;
- ``requirements.md``, when present, must itself be parseable and
  in-vocabulary (it anchors the derivation cascade);
- any phase whose leading token is ``parked`` must carry a
  ``Resume-Trigger:`` clause in the same file (R9 — parked specs
  cannot rot indefinitely).

Enforced CI-only via ``tests/unit/gates/test_status_line_gate.py``
sweeping ``docs/specs/`` (the D7 pattern — pre-commit is not
guaranteed an importable ``attune``).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path

from attune.ops.spec_lifecycle import STATUS_VOCABULARY, _normalize
from attune.ops.specs_data import _PHASE_FILES, _extract_status

from .protocol import GateReceipt

#: Clause R9 requires on any ``parked`` status (case-sensitive — the
#: backfilled convention writes it verbatim).
RESUME_TRIGGER_CLAUSE = "Resume-Trigger:"


def status_line_gate(spec_dir: Path, *, phase: str = "verification") -> GateReceipt:
    """Return a receipt for one spec directory's status legibility."""
    findings: list[str] = []
    parseable = 0
    for fname in _PHASE_FILES:
        file = spec_dir / fname
        if not file.is_file():
            continue
        try:
            text = file.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(f"{fname}: unreadable ({exc})")
            continue
        status = _extract_status(text)
        if status is None:
            if fname == "requirements.md":
                findings.append("requirements.md: no parseable **Status:** line")
            continue
        token = _normalize(status)
        if token not in STATUS_VOCABULARY:
            findings.append(
                f"{fname}: leading status token {token!r} not in vocabulary "
                f"(write '**Status:** <token> (<date>) — <annotation>')"
            )
            continue
        parseable += 1
        if token == "parked" and RESUME_TRIGGER_CLAUSE not in text:
            findings.append(
                f"{fname}: 'parked' without a {RESUME_TRIGGER_CLAUSE} clause "
                "(R9 — a date, a dependency milestone, or 'evergreen')"
            )
    if parseable == 0:
        findings.append("no phase file carries a parseable, in-vocabulary **Status:** line")
    return GateReceipt(
        gate_id="status-line",
        phase=phase,
        target=spec_dir.name,
        state="REVISE" if findings else "PASS",
        findings=findings,
        evidence_refs=[f"vocabulary: {', '.join(sorted(STATUS_VOCABULARY))}"],
        proposed_disposition=(
            "normalize the status line(s) token-first" if findings else "proceed"
        ),
    )
