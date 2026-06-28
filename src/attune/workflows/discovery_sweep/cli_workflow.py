"""CLI glue for discovery-sweep — source list assembly.

Lives outside ``workflow.py`` so the engine doesn't import the
sources (and their transitive dependencies) until the user actually
runs a sweep. ``default_sources()`` returns all seven adapters
(Phase 2B): the non-LLM pattern scanner plus six LLM adapters.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .sources.bug_predict import BugPredictSource
from .sources.dependency_check import DependencyCheckSource
from .sources.doc_audit import DocAuditSource
from .sources.pattern_scan import PatternScanSource
from .sources.perf_audit import PerfAuditSource
from .sources.security_audit import SecurityAuditSource
from .sources.test_audit import TestAuditSource
from .workflow import FindingSource


def default_sources() -> list[FindingSource]:
    """Return the default source list for ``attune workflow run discovery-sweep``.

    Phase 2B complete: pattern scanner plus six LLM adapters
    (bug-predict, security-audit, dependency-check, perf-audit,
    doc-audit, test-audit). Order isn't load-bearing; verification
    rules dedup by location regardless of source emission order.
    """
    return [
        PatternScanSource(),
        BugPredictSource(),
        SecurityAuditSource(),
        DependencyCheckSource(),
        PerfAuditSource(),
        DocAuditSource(),
        TestAuditSource(),
    ]


__all__ = ["default_sources"]
