"""The shared gate protocol (spec-lifecycle-gates RR-1/RR-2).

One machine-readable receipt shape for every gate at every lifecycle
boundary, with a CLOSED four-state disposition enum — adding a state
requires a spec amendment (the ``FAILURE_CODES`` discipline). A gate
may BLOCK, REVISE, or REPORT with exact shortfalls; it never advances
a phase (RR-2): callers render receipts, a human moves the work.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

#: The five lifecycle boundaries gates fire at (RR-1).
PHASES: tuple[str, ...] = (
    "brainstorm",
    "requirements",
    "design",
    "tasks",
    "execution",
    "verification",
)

#: Closed disposition states (RR-1). A spec amendment is required to
#: extend this — unknown states are bugs, not new categories.
STATES: tuple[str, ...] = ("PASS", "REVISE", "CHAIR_REQUIRED", "BLOCKED")


@dataclass
class GateReceipt:
    """One gate evaluation's machine-readable receipt (RR-1).

    ``findings`` carries EXACT shortfalls (the corpus-readiness
    idiom) — never a bare verdict. ``decisions_ref`` is set only when
    a chair ruling later cites this receipt; the receipt itself never
    writes decisions.md (G1).
    """

    gate_id: str
    phase: str
    target: str  # spec slug or artifact path
    state: str
    findings: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    proposed_disposition: str = ""
    waived: bool = False
    receipt_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decisions_ref: str | None = None

    def __post_init__(self) -> None:
        if self.state not in STATES:
            raise ValueError(f"unknown gate state: {self.state!r} (closed enum {STATES})")
        if self.phase not in PHASES:
            raise ValueError(f"unknown phase: {self.phase!r} (must be one of {PHASES})")

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable form for the verdict ledger."""
        return {
            "receipt_id": self.receipt_id,
            "gate_id": self.gate_id,
            "phase": self.phase,
            "target": self.target,
            "state": self.state,
            "findings": list(self.findings),
            "evidence_refs": list(self.evidence_refs),
            "proposed_disposition": self.proposed_disposition,
            "waived": self.waived,
            "timestamp": self.timestamp,
            "decisions_ref": self.decisions_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GateReceipt:
        """Load a ledger row back into a receipt (round-trip)."""
        return cls(
            gate_id=str(data["gate_id"]),
            phase=str(data["phase"]),
            target=str(data["target"]),
            state=str(data["state"]),
            findings=list(data.get("findings", [])),
            evidence_refs=list(data.get("evidence_refs", [])),
            proposed_disposition=str(data.get("proposed_disposition", "")),
            waived=bool(data.get("waived", False)),
            receipt_id=str(data.get("receipt_id", uuid.uuid4().hex[:12])),
            timestamp=str(data.get("timestamp", "")),
            decisions_ref=data.get("decisions_ref"),
        )
