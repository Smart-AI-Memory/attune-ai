"""Discovery-sweep source adapters.

Each adapter implements :class:`attune.workflows.discovery_sweep.FindingSource`.
All seven ship and run (Phase 2B): the non-LLM :class:`PatternScanSource`
plus six LLM adapters (bug-predict, security-audit, dependency-check,
perf-audit, doc-audit, test-audit). The full set is wired in
:func:`attune.workflows.discovery_sweep.cli_workflow.default_sources`,
which imports each adapter from its own module (this package's
``__all__`` re-exports only ``PatternScanSource`` for backward
compatibility).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .pattern_scan import PatternScanSource

__all__ = ["PatternScanSource"]
