"""Curator data model — frozen dataclasses for sources and results.

See docs/specs/bulletin-curator/design.md for the contract.

Source readers return :class:`SourceSummary`. The orchestrator
synthesises across them and returns a :class:`CuratorResult`. All
dataclasses are frozen so the cache layer can rely on them as
value objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Severity = Literal["info", "nudge", "warn", "block"]
ActionKind = Literal["ask", "open", "run", "dismiss"]


@dataclass(frozen=True)
class SourceItem:
    """One row from a source — a unit the curator can cite.

    ``item_id`` is the stable handle the LLM uses in its
    ``sources`` array. The orchestrator validates that every cited
    id resolves back to a known item before returning the result.
    """

    item_id: str
    title: str
    detail: str
    link: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceSummary:
    """The output of one source reader.

    ``state_hash`` MUST be deterministic for the same logical
    state — the cache layer keys on it. ``items=[]`` is a valid
    empty result; readers must not raise.
    """

    source_id: str
    state_hash: str
    items: list[SourceItem] = field(default_factory=list)
    fetch_ms: int = 0


@dataclass(frozen=True)
class SuggestedAction:
    """The actionable footer of a CuratorItem.

    ``kind`` selects which of the optional fields are meaningful.
    The dashboard / CLI render the kind-appropriate UI.
    """

    kind: ActionKind
    label: str | None = None
    question: str | None = None
    choices: list[str] = field(default_factory=list)
    url: str | None = None
    workflow: str | None = None
    scope: str | None = None


@dataclass(frozen=True)
class CuratorItem:
    """One ranked attention item.

    ``sources`` is a list of ``SourceItem.item_id`` values — the
    orchestrator drops any item that cites an unknown id.
    """

    id: str
    title: str
    severity: Severity
    rationale: str
    sources: list[str] = field(default_factory=list)
    suggested_action: SuggestedAction | None = None


@dataclass(frozen=True)
class CuratorResult:
    """The synthesised briefing returned by ``run_curator``.

    Cached as JSON under ``<attune_home>/curator-cache/<key>.json``
    by :class:`attune.curator.cache.CuratorCache`.
    """

    summary: str
    items: list[CuratorItem] = field(default_factory=list)
    sources_consulted: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    cached_at: datetime | None = None
    model: str = ""
