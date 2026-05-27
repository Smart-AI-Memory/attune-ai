"""Bulletin Curator — on-demand briefing across project surfaces.

See ``docs/specs/bulletin-curator/`` for the spec.
"""

from __future__ import annotations

from .result import (
    ActionKind,
    CuratorItem,
    CuratorResult,
    Severity,
    SourceItem,
    SourceSummary,
    SuggestedAction,
)
from .sources import SourceReader

__all__ = [
    "ActionKind",
    "CuratorItem",
    "CuratorResult",
    "Severity",
    "SourceItem",
    "SourceReader",
    "SourceSummary",
    "SuggestedAction",
]
