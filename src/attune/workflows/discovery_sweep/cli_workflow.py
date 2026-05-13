"""Default source list for ``attune workflow run discovery-sweep``.

Phase 1 ships only the deterministic :class:`PatternScanSource`.
LLM adapters are wired in Phase 2 (P2.1–P2.6). The Protocol
contract is the source of truth, not this list.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from .sources import PatternScanSource
from .workflow import FindingSource


def default_sources() -> list[FindingSource]:
    """Return the default source list. Phase 1: pattern-scan only."""
    return [PatternScanSource()]


__all__ = ["default_sources"]
