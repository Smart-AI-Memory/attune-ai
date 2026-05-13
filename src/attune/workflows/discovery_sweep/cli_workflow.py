"""CLI glue for discovery-sweep — source list assembly.

Lives outside ``workflow.py`` so the engine doesn't import the
sources (and their transitive dependencies) until the user actually
runs a sweep. Phase 1 returns the pattern source only; Phase 2A+
appends LLM adapters.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .sources.pattern_scan import PatternScanSource
from .workflow import FindingSource


def default_sources() -> list[FindingSource]:
    """Return the default source list for ``attune workflow run discovery-sweep``.

    Phase 1: pattern scanner only. Phase 2A+ adds LLM adapters
    (bug-predict, security-audit, dependency-check, perf-audit,
    doc-audit) — register them here, in spec order, when the
    adapters land.
    """
    return [PatternScanSource()]


__all__ = ["default_sources"]
