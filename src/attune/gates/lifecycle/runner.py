"""Boundary gate runner (spec-lifecycle-gates RR-2/RR-5).

Selects gates via the activation policy, runs them SERIALLY, appends
every receipt to the G1 ledger, and returns them. It never advances
anything and never mutates spec files — callers render receipts and
a human moves the phase (RR-2). G5 exit semantics live with the CLI
caller: BLOCKED → 2, CHAIR_REQUIRED → 1, else 0.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path

from . import activation, baseline, ledger
from .protocol import GateReceipt


def _document_for(spec_dir: Path, phase: str) -> str:
    """The boundary's artifact text: the highest-phase file at or
    below ``phase`` (the reconciler's phase-precedence rule)."""
    order = ["tasks.md", "design.md", "requirements.md"]
    allowed = {
        "requirements": ["requirements.md"],
        "design": ["design.md", "requirements.md"],
        "tasks": order,
    }.get(phase, order)
    for name in allowed:
        candidate = spec_dir / name
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    return ""


def run_boundary(
    phase: str,
    spec_slug: str,
    *,
    project_root: Path,
    tier: str = "spec",
    changed_paths: list[str] | None = None,
    ledger_file: Path | None = None,
) -> list[GateReceipt]:
    """Run the boundary's active gates over the spec's artifact.

    Returns every receipt (already ledger-appended). Unexpired chair
    waivers downgrade their gate to PASS with ``waived=True`` — the
    receipt still logs (G2).
    """
    spec_dir = project_root / "docs" / "specs" / spec_slug
    document = _document_for(spec_dir, phase)
    radius = activation.blast_radius(changed_paths or [])
    gates = activation.active_gates(tier, radius)
    decisions = spec_dir / "decisions.md"
    waivers = activation.parse_waivers(
        decisions.read_text(encoding="utf-8") if decisions.is_file() else ""
    )

    receipts: list[GateReceipt] = []
    for gate_id in gates:
        if gate_id == "symbol-reality":
            receipt = baseline.symbol_reality_gate(
                document, project_root, phase=phase, target=spec_slug, extra_roots=(spec_dir,)
            )
        elif gate_id == "falsifiability":
            receipt = baseline.falsifiability_gate(document, phase=phase, target=spec_slug)
        elif gate_id == "format-lint" and phase == "requirements":
            receipt = baseline.format_lint_gate(document, "final", phase=phase, target=spec_slug)
        elif gate_id == "chair-review":
            receipt = GateReceipt(
                gate_id="chair-review",
                phase=phase,
                target=spec_slug,
                state="CHAIR_REQUIRED",
                findings=[f"blast radius 'chair' ({radius=})"],
                proposed_disposition="chair rules before this boundary advances",
            )
        else:
            continue  # boundary-inapplicable gate
        if receipt.state != "PASS" and activation.waived(gate_id, spec_slug, waivers):
            receipt.state = "PASS"
            receipt.waived = True
            receipt.proposed_disposition = "waived by unexpired chair waiver (G2)"
        ledger.append(receipt, path=ledger_file)
        receipts.append(receipt)
    return receipts


def exit_code(receipts: list[GateReceipt]) -> int:
    """G5 semantics: BLOCKED → 2 (hard), CHAIR_REQUIRED → 1 (soft), else 0."""
    states = {r.state for r in receipts}
    if "BLOCKED" in states:
        return 2
    if "CHAIR_REQUIRED" in states:
        return 1
    return 0
