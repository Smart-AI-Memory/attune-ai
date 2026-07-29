"""Spec-lifecycle quality gates (docs/specs/spec-lifecycle-gates/).

Autonomous gates BLOCK / REVISE / REPORT with exact shortfalls; only
the chair approves, waives, and advances. Verdicts persist to the G1
machine ledger, never to decisions.md.

Lives as a SUBPACKAGE of ``attune.gates`` — the parent package is the
collaboration-gates surface (spend gate); implementation discovered
the design's ``src/attune/gates/`` destination was already taken and
resolved to ``attune.gates.lifecycle`` (recorded in the spec's
decisions.md). The parent's dependency-light ``__init__`` is
untouched; import this subpackage directly.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .activation import (
    BASELINE_GATES,
    BATCH_THRESHOLD_FRACTION,
    LADDER_GATES,
    Waiver,
    active_gates,
    blast_radius,
    parse_waivers,
    waived,
)
from .baseline import falsifiability_gate, format_lint_gate, symbol_reality_gate
from .ledger import append, discharge, latest_for, ledger_path, unresolved_chair_required
from .protocol import PHASES, STATES, GateReceipt
from .runner import exit_code, run_boundary
from .status_line import RESUME_TRIGGER_CLAUSE, status_line_gate

__all__ = [
    "BASELINE_GATES",
    "BATCH_THRESHOLD_FRACTION",
    "LADDER_GATES",
    "PHASES",
    "STATES",
    "GateReceipt",
    "Waiver",
    "active_gates",
    "append",
    "blast_radius",
    "exit_code",
    "RESUME_TRIGGER_CLAUSE",
    "falsifiability_gate",
    "format_lint_gate",
    "latest_for",
    "ledger_path",
    "parse_waivers",
    "run_boundary",
    "status_line_gate",
    "symbol_reality_gate",
    "discharge",
    "unresolved_chair_required",
    "waived",
]
