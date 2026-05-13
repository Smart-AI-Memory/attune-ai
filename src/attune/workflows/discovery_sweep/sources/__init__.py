"""Built-in ``FindingSource`` adapters for discovery-sweep.

Phase 2A ships the deterministic pattern scanner — a fast,
zero-LLM-cost adapter that produces line-level findings via
regex/AST primitives. LLM-driven adapters wrapping
``BugPredictionWorkflow``, ``SecurityAuditWorkflow``, etc. are
Phase 2B work.
"""

from __future__ import annotations

from .pattern_scan import PatternScanSource

__all__ = ["PatternScanSource"]
