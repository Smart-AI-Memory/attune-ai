"""Diagnosis configuration — policy is data (advanced-debugging-plugin).

The dissent register requires every ``DiagnosisRecord`` to carry the
policy values used (``config_used``) rather than hard-coding them;
this module is the single place those values live.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any

#: Ordered confidence scale (weakest -> strongest). Hypothesis
#: confidence values come from this scale; the fix loop (Phase D)
#: compares against ``fix_proposal_threshold`` by index.
DEFAULT_CONFIDENCE_SCALE = ("low", "medium", "high")


@dataclass
class DiagnosisConfig:
    """Tunable policy for one diagnosis run."""

    confidence_scale: tuple[str, ...] = DEFAULT_CONFIDENCE_SCALE
    fix_proposal_threshold: str = "high"
    panel_seats: int = 2
    evidence_budget_bytes: int = 64 * 1024
    triage_batch_max: int = 5
    extra: dict[str, Any] = field(default_factory=dict)

    def to_config_used(self) -> dict[str, Any]:
        """The dict stamped into ``DiagnosisRecord.config_used``."""
        data = asdict(self)
        data["confidence_scale"] = list(self.confidence_scale)
        return data

    @classmethod
    def from_env(cls) -> DiagnosisConfig:
        """Build from ``ATTUNE_DIAGNOSIS_*`` env overrides (all optional)."""
        cfg = cls()
        threshold = os.environ.get("ATTUNE_DIAGNOSIS_FIX_THRESHOLD")
        if threshold in cfg.confidence_scale:
            cfg.fix_proposal_threshold = threshold
        for attr, env in (
            ("panel_seats", "ATTUNE_DIAGNOSIS_PANEL_SEATS"),
            ("evidence_budget_bytes", "ATTUNE_DIAGNOSIS_EVIDENCE_BUDGET"),
            ("triage_batch_max", "ATTUNE_DIAGNOSIS_TRIAGE_MAX"),
        ):
            raw = os.environ.get(env)
            if raw and raw.isdigit() and int(raw) > 0:
                setattr(cfg, attr, int(raw))
        return cfg
