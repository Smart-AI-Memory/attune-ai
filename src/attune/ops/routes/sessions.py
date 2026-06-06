"""JSON API for the /sessions surface.

Mirrors the ``/api/specs`` and ``/api/runs/...`` pattern: HTML
pages live in ``dashboard.py``, JSON endpoints live in a
subsystem-named module. Same data shape the HTML page consumes,
so dashboard consumers (CLI scripts, watch loops, future widgets)
can poll without parsing HTML.

Decision (ops-sessions-page decisions.md):
``GET /api/sessions`` returns
``{sessions: [{id, started_at, last_activity, duration_seconds,
message_count, starter_prompt, source}, ...]}``
where ``source`` is one of ``"heuristic" | "haiku" | "cached"``.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Request

from attune.ops import data, session_summarizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _enrich_sessions(
    pairs: list,
    *,
    attune_home,
    budget: session_summarizer.Budget,
) -> tuple[list[data.Session], bool]:
    """Run Haiku summarization over ``pairs`` and return enriched sessions.

    Each pair is ``(Session, Path)`` from
    :func:`data.list_recent_sessions_with_paths`. The original
    session's ``starter_prompt`` is replaced with the Haiku-or-cached
    summary when the summarizer succeeds; the heuristic text is kept
    when it returns ``None`` (LLM disabled, cache miss + over budget,
    or any failure path).

    Returns ``(enriched_sessions, over_budget)`` — the boolean flag
    tells the caller whether to render the "summary unavailable —
    over budget" marker. The flag latches at the first time the
    summarizer skips a session due to budget breach, so the marker
    appears once for the whole tail rather than per-row.
    """
    enriched: list[data.Session] = []
    over_budget = False
    for session, jsonl_path in pairs:
        # Mid-loop budget check: cached reads still happen post-breach
        # (free), but fresh calls don't. The summarizer's own
        # ``should_skip()`` handles this; we record the flag for the
        # template marker.
        breached_before = budget.breached
        result = session_summarizer.summarize_session(
            jsonl_path,
            attune_home=attune_home,
            budget=budget,
        )
        if result is None:
            if not breached_before and budget.breached:
                # Summarizer recorded a spend that crossed the cap; the
                # marker should fire for the trailing sessions.
                over_budget = True
            elif budget.breached:
                # Already-breached state; trailing sessions skip silently.
                over_budget = True
            enriched.append(session)
            continue
        enriched.append(
            data.Session(
                id=session.id,
                started_at=session.started_at,
                last_activity=session.last_activity,
                duration_seconds=session.duration_seconds,
                message_count=session.message_count,
                starter_prompt=result.text,
                source=result.source,
            )
        )
    return enriched, over_budget


def enrich_with_summaries(
    project_root,
    attune_home,
    *,
    days: int = 3,
    limit: int | None = data.DEFAULT_SESSION_LIST_CAP,
    budget: session_summarizer.Budget | None = None,
) -> tuple[list[data.Session], bool]:
    """Public helper used by both the JSON route and the HTML page.

    Reads the recent-sessions list (with paths) and runs the
    summarizer over each. Returns ``(sessions, over_budget)``. The
    HTML page passes the same flag through to the template; the JSON
    endpoint surfaces it in the response under
    ``meta.budget_exceeded``.
    """
    pairs = data.list_recent_sessions_with_paths(project_root, days=days, limit=limit)
    if budget is None:
        budget = session_summarizer.new_budget()
    return _enrich_sessions(pairs, attune_home=attune_home, budget=budget)


@router.get("")
async def list_sessions(request: Request) -> dict[str, Any]:
    """``GET /api/sessions`` — JSON listing of recent sessions.

    Same enrichment path the HTML page uses, so the two views can't
    drift on the ``source`` field (heuristic vs haiku vs cached).
    Empty list is a legitimate response; the caller shouldn't treat
    it as an error.
    """
    cfg = request.app.state.config
    # ``enrich_with_summaries`` calls the SYNCHRONOUS Anthropic SDK
    # client (``anthropic.Anthropic(...).messages.create()``) inside a
    # per-session loop. Calling it directly from this async route
    # blocks the uvicorn event loop for the duration of the Haiku
    # batch (~0.5–2s per session × N sessions), freezing every other
    # request — SSE streams, runner control, page renders. Defer the
    # blocking chain to a thread; the ``anthropic`` SDK is documented
    # thread-safe. Preserves the existing sync API of
    # ``summarize_session`` (used by tests and other paths).
    sessions, over_budget = await asyncio.to_thread(
        enrich_with_summaries,
        cfg.project_root,
        cfg.attune_home,
    )
    return {
        "sessions": [asdict(s) for s in sessions],
        "meta": {
            "budget_exceeded": over_budget,
            "llm_enabled": session_summarizer.llm_enabled(),
        },
    }
