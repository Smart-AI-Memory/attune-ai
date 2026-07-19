"""Risk-tiered gate activation (spec-lifecycle-gates RR-3/RR-4/RR-8).

Pure functions, no I/O beyond reading a decisions.md text the caller
supplies: blast-radius classification over the chair-ruled surface
map (G3), tier-based gate selection, and parse-only waiver reading
with expiry (G2/G5). Unclassifiable changes escalate — the
conservative default is always ``chair``.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

#: The chair-ruled always-chair surface map (design.md, RR-3). Path
#: prefixes and basename patterns checked against repo-relative paths.
_CHAIR_PREFIXES: tuple[str, ...] = (
    "src/attune/security/",
    "plugin/",
    ".github/workflows/",
    "src/attune/models/telemetry/data_models.py",
)
_CHAIR_BASENAMES: tuple[str, ...] = ("pyproject.toml", "__init__.py")

#: The mandatory mechanical baseline (G3): fully-autonomous gates
#: that run for EVERY tier, including sub-spec work.
BASELINE_GATES: tuple[str, ...] = ("symbol-reality", "falsifiability")

#: The full ladder for spec-tier work (RR-4). Boundary-specific
#: selection happens in the runner; this is the ordered superset.
LADDER_GATES: tuple[str, ...] = (
    "symbol-reality",
    "falsifiability",
    "format-lint",
)

#: G4: batching engages when gate-generated CHAIR_REQUIRED volume
#: exceeds this fraction of the measured weekly ruling baseline.
BATCH_THRESHOLD_FRACTION = 0.20

#: WAIVER: <gate_id> <target> until <YYYY-MM-DD> — <reason> (G2).
_WAIVER_RE = re.compile(
    r"^WAIVER:\s+(?P<gate>[\w-]+)\s+(?P<target>\S+)\s+until\s+"
    r"(?P<until>\d{4}-\d{2}-\d{2})\s+—\s+(?P<reason>.+)$",
    re.MULTILINE,
)


def blast_radius(changed_paths: list[str]) -> str:
    """Classify a change set: ``"isolated"`` or ``"chair"`` (RR-3).

    Deletions, migrations, and anything touching the ruled surface
    map escalate; an EMPTY change set is unclassifiable and therefore
    ``chair`` (the conservative default, ruled).
    """
    if not changed_paths:
        return "chair"
    for raw in changed_paths:
        path = raw.strip().replace("\\", "/")
        if not path:
            return "chair"
        if any(path.startswith(p) for p in _CHAIR_PREFIXES):
            return "chair"
        if path.rsplit("/", 1)[-1] in _CHAIR_BASENAMES:
            return "chair"
        if "migration" in path.lower():
            return "chair"
    return "isolated"


def active_gates(tier: str, radius: str) -> list[str]:
    """Select the gate set for a work tier + blast radius (RR-4/G3).

    ``tier`` is ``"sub-spec"`` (inline edits, one-shots — the
    xml-enhanced-prompts "Do NOT use" list) or ``"spec"``. Sub-spec
    work sees only the mandatory baseline regardless of radius —
    the ceremony-inflation guard.
    """
    if tier == "sub-spec":
        return list(BASELINE_GATES)
    gates = list(LADDER_GATES)
    return gates if radius == "isolated" else [*gates, "chair-review"]


@dataclass(frozen=True)
class Waiver:
    """One parsed, chair-authored waiver line (G2)."""

    gate_id: str
    target: str
    until: str  # YYYY-MM-DD
    reason: str

    def expired(self, *, today: datetime | None = None) -> bool:
        """True when the waiver's date has passed (UTC date compare)."""
        now = (today or datetime.now(timezone.utc)).date().isoformat()
        return now > self.until


def parse_waivers(decisions_text: str) -> list[Waiver]:
    """Extract WAIVER lines from a decisions.md text (parse-only).

    Malformed lines are ignored — a waiver the parser cannot read is
    a waiver that does not apply (fail-closed, per G2's
    never-self-granted rule).
    """
    return [
        Waiver(
            gate_id=m.group("gate"),
            target=m.group("target"),
            until=m.group("until"),
            reason=m.group("reason").strip(),
        )
        for m in _WAIVER_RE.finditer(decisions_text)
    ]


def waived(
    gate_id: str,
    target: str,
    waivers: list[Waiver],
    *,
    today: datetime | None = None,
) -> bool:
    """True when an unexpired chair waiver covers this gate+target."""
    return any(
        w.gate_id == gate_id and w.target == target and not w.expired(today=today) for w in waivers
    )
