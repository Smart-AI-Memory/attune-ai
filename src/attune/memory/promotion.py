"""Stash → curated promotion path (curated-memory R4).

A deliberate, reviewable step that moves auto-stashed session findings
into the durable curated graph: the agent drafts a curated node per
candidate (the 30-day test — "will this still be true and worth
carrying in a month?"), the reviewer verdicts each one through a
decision form, and every promotion writes provenance metadata (source
stash entry, review verdict, date) onto the resulting node.

Bulk import is explicitly wrong (the 2026-07-02 auto-stash
supersession contradiction is the evidence) — this module has no
promote-all path; every node requires an explicit per-candidate
verdict.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from attune.memory.graph import MemoryGraph
from attune.memory.session_stash import recent_entries

logger = logging.getLogger(__name__)

#: Node types admissible in the curated graph (see attune.memory.nodes).
CURATED_TYPES = ("user_context", "feedback", "project_context", "reference")


def promotion_candidates(
    top_k: int = 10, cwd: str | None = None, backend: Any = None
) -> list[dict[str, Any]]:
    """Fetch recent stashed findings as promotion candidates.

    Reads through the same backend resolution the stash hook writes
    through (file by default, AMS/Redis when connected), normalizing
    the backend-shaped records to a stable candidate shape.

    Args:
        top_k: Max candidates to fetch (newest first).
        cwd: When set, prefer entries from this project root.
        backend: Optional injected backend (tests); resolved from the
            entry point when omitted.

    Returns:
        Candidate dicts: ``{id, text, stash_type, session_id, ts}``.
    """
    records = recent_entries(top_k=top_k, cwd=cwd, backend=backend)
    candidates = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        topics = rec.get("topics") or []
        if isinstance(topics, str):
            topics = topics.split(",")
        stash_type = next(
            (t.split(":", 1)[1] for t in topics if isinstance(t, str) and t.startswith("type:")),
            "note",
        )
        candidates.append(
            {
                "id": str(rec.get("id", "")),
                "text": str(rec.get("text", "")),
                "stash_type": stash_type,
                "session_id": str(rec.get("session_id", "")),
                "ts": rec.get("ts", rec.get("created_at")),
            }
        )
    return candidates


def promotion_form_dict(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the per-candidate verdict form (one decision per proposal).

    Each proposal renders as a Promote/Skip decision card whose
    rationale carries the drafted node text and its stash provenance —
    so the reviewer verdicts each candidate individually (no bulk
    accept). Feed the result to :func:`attune.elicitation.form_from_dict`.

    Args:
        proposals: Drafted nodes, each ``{source_id, type, name,
            description, tags?}`` where ``source_id`` is the stash
            entry id and ``type`` is a curated node type.

    Returns:
        A form dict; answers map ``promote_<i>`` → "Promote" | "Skip".
    """
    fields = []
    for i, prop in enumerate(proposals):
        fields.append(
            {
                "id": f"promote_{i}",
                "text": f"[{prop.get('type', '?')}] {prop.get('name', '')}",
                "type": "decision",
                "options": ["Promote", "Skip"],
                "recommended": "Promote",
                "rationale": (
                    f"{prop.get('description', '')}\n" f"(from stash {prop.get('source_id', '?')})"
                ),
            }
        )
    return {
        "title": "Stash → curated promotion",
        "description": (
            "Per-candidate verdict — promote only what passes the 30-day "
            "test. Skipped candidates stay in the stash."
        ),
        "fields": fields,
    }


def promote(
    proposal: dict[str, Any],
    source: dict[str, Any],
    response_id: str = "",
    graph: MemoryGraph | None = None,
) -> str:
    """Write one verdicted proposal into the curated graph with provenance.

    Args:
        proposal: The drafted node — ``{type, name, description, tags?}``;
            ``type`` must be one of :data:`CURATED_TYPES`.
        source: The stash candidate it came from (see
            :func:`promotion_candidates`) — recorded as provenance.
        response_id: The review response id (the form submission that
            carried the "Promote" verdict).
        graph: Target graph; defaults to :meth:`MemoryGraph.curated`.

    Returns:
        The created node id.

    Raises:
        ValueError: If ``proposal['type']`` is not a curated node type.
    """
    node_type = proposal.get("type", "")
    if node_type not in CURATED_TYPES:
        raise ValueError(
            f"promotion requires a curated node type {CURATED_TYPES}, got {node_type!r}"
        )
    target = graph if graph is not None else MemoryGraph.curated()
    provenance = {
        "promoted_from_stash_id": str(source.get("id", "")),
        "promoted_from_session": str(source.get("session_id", "")),
        "promoted_from_ts": source.get("ts"),
        "promoted_at": datetime.now().strftime("%Y-%m-%d"),
        "review_verdict": "promote",
        "review_response_id": response_id,
    }
    node_id = target.add_finding(
        workflow="",
        finding={
            "type": node_type,
            "name": proposal.get("name", ""),
            "description": proposal.get("description", ""),
            "tags": proposal.get("tags", []),
            "metadata": provenance,
            # add_finding defaults to "open"; hydration + the recall digest
            # only carry "active" nodes — an "open" promotion would be
            # invisible to recall (caught live in the R4 dogfood).
            "status": "active",
        },
    )
    logger.info("promoted stash %s -> curated node %s", source.get("id"), node_id)
    return node_id
