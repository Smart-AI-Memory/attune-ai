"""Discovery Sweep — meta-workflow that fans out audits and triages findings.

See ``docs/specs/discovery-sweep/`` for the approved spec.

Phase 1 ships the engine, the ``FindingSource`` Protocol,
deterministic verification rules, CLI registration, and a
non-LLM ``PatternScanSource`` adapter. LLM source adapters
(bug-predict, security-audit, dependency-check, perf-audit,
doc-audit) arrive in Phase 2.
"""

from __future__ import annotations

from .verification import RouteDecision, route_finding
from .workflow import (
    DiscoverySweepWorkflow,
    Finding,
    FindingSource,
    QuestionFinding,
    RejectedFinding,
    Severity,
    SweepMetadata,
    SweepResult,
)

__all__ = [
    "DiscoverySweepWorkflow",
    "Finding",
    "FindingSource",
    "QuestionFinding",
    "RejectedFinding",
    "RouteDecision",
    "Severity",
    "SweepMetadata",
    "SweepResult",
    "route_finding",
]
