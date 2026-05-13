"""CLI glue for discovery-sweep — source list assembly.

Lives outside ``workflow.py`` so the engine doesn't import the
sources (and their transitive dependencies) until the user actually
runs a sweep. Phase 1 returns the pattern source only; Phase 2A+
appends LLM adapters.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .sources.bug_predict import BugPredictSource
from .sources.dependency_check import DependencyCheckSource
from .sources.pattern_scan import PatternScanSource
from .sources.perf_audit import PerfAuditSource
from .sources.security_audit import SecurityAuditSource
from .workflow import FindingSource


def default_sources() -> list[FindingSource]:
    """Return the default source list for ``attune workflow run discovery-sweep``.

    Phase 1: pattern scanner only. Phase 2 adds LLM adapters in
    spec order (bug-predict, security-audit, dependency-check,
    perf-audit, doc-audit, test-audit) — append here as each lands.
    Order isn't load-bearing; verification rules dedup by location
    regardless of source emission order.
    """
    return [
        PatternScanSource(),
        BugPredictSource(),
        SecurityAuditSource(),
        DependencyCheckSource(),
        PerfAuditSource(),
    ]


__all__ = ["default_sources"]
