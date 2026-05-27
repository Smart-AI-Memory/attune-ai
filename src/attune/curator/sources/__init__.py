"""Source readers for the bulletin curator.

Each reader is a pure-Python module exporting a top-level
``read(*, project_root, since=None) -> SourceSummary`` function
that matches the :class:`SourceReader` Protocol. Readers must NOT
raise — empty / unreadable sources return an empty
``SourceSummary``. The curator orchestrator can tolerate any
individual source being silent; it cannot tolerate one source
crashing the run.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from ..result import SourceSummary


class SourceReader(Protocol):
    """Shape every source reader implements at module level."""

    def read(
        self,
        *,
        project_root: Path,
        since: datetime | None = None,
    ) -> SourceSummary:
        """Return a compact summary of this source's current state.

        Must not raise. Empty / unreadable sources return an
        empty ``SourceSummary`` whose ``state_hash`` is stable
        across calls.
        """


__all__ = ["SourceReader"]
