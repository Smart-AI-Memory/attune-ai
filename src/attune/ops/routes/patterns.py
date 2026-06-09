"""Dashboard surface for the pattern review queue (pattern-review-queue R6).

A human-in-the-loop checkpoint, mirrored from the CLI
(``attune patterns review|promote|reject``):

- ``GET /patterns`` — render the staged-pattern queue as review cards
  (name, type, confidence, source agent, description, code preview).
- ``POST /patterns/promote`` — promote a staged pattern into the durable
  :class:`~attune.pattern_review.PersistentPatternLibrary`, then drop it
  from the queue. Token-gated.
- ``POST /patterns/reject`` — drop a staged pattern with an audit reason.
  Token-gated.

The mutating routes use the existing ``X-Attune-Client`` token gate
(:func:`attune.ops.security.require_client_token`) for defense in depth,
matching the curator / specs / runner mutating routes.

The queue and the promote target share one backend so the
``staged_pattern:`` and ``pattern:`` prefixes live in the same store
(the local file backend by default, the Redis Agent Memory Server when
configured) — the same store the CLI manages, so the dashboard and CLI
show one queue.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse

from attune.ops.security import require_client_token
from attune.pattern_review import PatternReviewQueue, PersistentPatternLibrary

from .dashboard import _ctx

if TYPE_CHECKING:
    from attune.memory.backend import MemoryBackend

logger = logging.getLogger(__name__)

router = APIRouter()


def _backend(request: Request) -> MemoryBackend | None:
    """Backend override from ``app.state`` (tests inject a tmp backend).

    ``None`` in production → the queue/library resolve their own default
    backend (file by default; AMS when configured), the same store the
    ``attune patterns`` CLI manages.
    """
    return getattr(request.app.state, "pattern_backend", None)


def _queue(request: Request) -> PatternReviewQueue:
    return PatternReviewQueue(_backend(request))


def _library(request: Request) -> PersistentPatternLibrary:
    return PersistentPatternLibrary(_backend(request))


@router.get("/patterns", response_class=HTMLResponse)
async def patterns_page(request: Request) -> HTMLResponse:
    """Render the staged-pattern review queue (newest-highest-confidence first)."""
    staged = _queue(request).list()
    templates = request.app.state.templates
    ctx = _ctx(request, page="patterns", staged=staged)
    return templates.TemplateResponse(request, "patterns.html", ctx)


@router.post("/patterns/promote")
async def patterns_promote(
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    """Promote a staged pattern into the durable library, then drop it.

    Body: ``{"pattern_id": "..."}``. Returns 404 if the id isn't staged,
    409 if the active library already holds that id (the pattern stays
    staged so the reviewer can rename or reject).
    """
    pattern_id = str(body.get("pattern_id") or "").strip()
    if not pattern_id:
        return JSONResponse({"ok": False, "error": "pattern_id required"}, status_code=400)

    queue = _queue(request)
    try:
        promoted = queue.promote(pattern_id, _library(request))
    except ValueError as exc:
        # Duplicate id in the active library — leave it staged for the reviewer.
        logger.info("patterns: promote conflict for %s: %s", pattern_id, exc)
        return JSONResponse({"ok": False, "error": "already in library"}, status_code=409)

    if promoted is None:
        return JSONResponse({"ok": False, "error": "not staged"}, status_code=404)
    return JSONResponse({"ok": True, "pattern_id": pattern_id})


@router.post("/patterns/reject")
async def patterns_reject(
    request: Request,
    body: dict[str, Any] = Body(...),  # noqa: B008
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    """Drop a staged pattern. The reason is recorded in the audit log.

    Body: ``{"pattern_id": "...", "reason": "..."}``. ``removed`` is
    ``False`` (with 404) when the id wasn't staged.
    """
    pattern_id = str(body.get("pattern_id") or "").strip()
    if not pattern_id:
        return JSONResponse({"ok": False, "error": "pattern_id required"}, status_code=400)
    reason = str(body.get("reason") or "").strip()

    removed = _queue(request).reject(pattern_id, reason)
    if not removed:
        return JSONResponse({"ok": False, "error": "not staged"}, status_code=404)
    return JSONResponse({"ok": True, "pattern_id": pattern_id, "removed": True})
