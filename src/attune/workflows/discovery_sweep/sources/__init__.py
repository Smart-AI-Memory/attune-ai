"""FindingSource adapters for discovery-sweep.

Phase 1 ships :class:`PatternScanSource` only. LLM adapters
(bug-predict, security-audit, dependency-check, perf-audit,
doc-audit) arrive in Phase 2.
"""

from __future__ import annotations

from .pattern_scan import PatternScanSource

__all__ = ["PatternScanSource"]
