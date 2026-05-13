"""Discovery-sweep source adapters.

Each adapter implements :class:`attune.workflows.discovery_sweep.FindingSource`.
Phase 1 ships only the non-LLM :class:`PatternScanSource`; the LLM
adapter cluster lands in Phase 2.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from .pattern_scan import PatternScanSource

__all__ = ["PatternScanSource"]
