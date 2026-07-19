"""CLI commands for the spec-lifecycle quality gates.

``attune gates check <phase> --spec <slug>`` runs the boundary's
active gates, renders every receipt, and exits per G5: BLOCKED → 2
(hard block), CHAIR_REQUIRED → 1 (soft block — proceed only with an
explicit chair acknowledgment), else 0.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path


def cmd_gates_check(args: Namespace) -> int:
    """Run boundary gates for a spec phase and render receipts (G5)."""
    from attune.gates.lifecycle import exit_code, run_boundary

    receipts = run_boundary(
        args.phase,
        args.spec,
        project_root=Path.cwd(),
        tier=args.tier,
        changed_paths=list(args.changed or []),
    )
    if not receipts:
        print(f"no gates applicable at the {args.phase} boundary for {args.spec}")
        return 0
    for r in receipts:
        flag = " (waived)" if r.waived else ""
        print(f"[{r.state}{flag}] {r.gate_id} — {r.target} @ {r.phase} ({r.receipt_id})")
        for finding in r.findings:
            print(f"    - {finding}")
        if r.proposed_disposition:
            print(f"    → {r.proposed_disposition}")
    code = exit_code(receipts)
    if code == 2:
        print("BLOCKED: this boundary cannot advance (G5 hard block).")
    elif code == 1:
        print("CHAIR_REQUIRED: proceed only with an explicit chair acknowledgment (G5).")
    return code
