"""Data classes for the discovery-sweep workflow.

Defines the Finding dataclass and enums consumed by the
verification rule engine, the complexity classifier, and the
serialization layer.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    """Outcome of the verification layer on a single finding."""

    ACCEPT = "accept"
    REJECT = "reject"
    UNSURE = "unsure"


class ResolutionComplexity(str, Enum):
    """Resolution-time tag for ACCEPTed findings.

    Drives Patrick's triage filter. ``needs_patrick`` flips when
    any complexity trigger fires (cross-cutting, security-adjacent,
    lesson-contradicting, etc.). Default is ``routine``.
    """

    ROUTINE = "routine"
    NEEDS_PATRICK = "needs_patrick"


class Severity(str, Enum):
    """Severity reported by the source sub-workflow."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _now_utc_iso() -> str:
    """Timezone-aware UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _new_sweep_id() -> str:
    """New short id for a sweep run."""
    return uuid.uuid4().hex[:12]


@dataclass
class Finding:
    """A single finding from a discovery sub-workflow.

    Carries the original finding plus the verification verdict and
    (when ACCEPTed) the resolution-complexity tag.

    Fields tagged optional in the schema are populated as the
    finding moves through the pipeline:
      - verification_status / verification_reasoning: set by the
        verification engine
      - resolution_complexity: set by the complexity classifier
        ONLY when verification_status == ACCEPT
      - estimated_fix_cost: reserved for future cost-aware triage
        (Phase 2); always None today
    """

    source_workflow: str
    file_path: str
    severity: Severity
    message: str
    raw_finding: dict[str, Any]
    sweep_id: str

    line: int | None = None
    verification_status: VerificationStatus = VerificationStatus.UNSURE
    verification_reasoning: str = ""
    resolution_complexity: ResolutionComplexity | None = None
    timestamp_utc: str = field(default_factory=_now_utc_iso)
    estimated_fix_cost: float | None = None

    def to_jsonl_dict(self) -> dict[str, Any]:
        """Serialize to a JSONL-friendly dict.

        Enums collapse to their string values; the dict round-trips
        cleanly through ``from_jsonl_dict``.
        """
        payload = asdict(self)
        payload["severity"] = self.severity.value
        payload["verification_status"] = self.verification_status.value
        payload["resolution_complexity"] = (
            self.resolution_complexity.value if self.resolution_complexity is not None else None
        )
        return payload

    @classmethod
    def from_jsonl_dict(cls, data: dict[str, Any]) -> Finding:
        """Deserialize from a JSONL-friendly dict."""
        return cls(
            source_workflow=data["source_workflow"],
            file_path=data["file_path"],
            severity=Severity(data["severity"]),
            message=data["message"],
            raw_finding=data["raw_finding"],
            sweep_id=data["sweep_id"],
            line=data.get("line"),
            verification_status=VerificationStatus(
                data.get("verification_status", VerificationStatus.UNSURE.value)
            ),
            verification_reasoning=data.get("verification_reasoning", ""),
            resolution_complexity=(
                ResolutionComplexity(data["resolution_complexity"])
                if data.get("resolution_complexity") is not None
                else None
            ),
            timestamp_utc=data.get("timestamp_utc", _now_utc_iso()),
            estimated_fix_cost=data.get("estimated_fix_cost"),
        )


__all__ = [
    "Finding",
    "ResolutionComplexity",
    "Severity",
    "VerificationStatus",
    "_new_sweep_id",
]
