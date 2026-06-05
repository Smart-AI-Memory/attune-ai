"""HTTP API for dashboard UI interaction counters.

Phase 6.1 of ops-runner-tier2. Two endpoints:

- ``POST /api/telemetry/interaction`` — increment a counter
- ``GET /api/telemetry/interactions`` — read the snapshot

Body validation is intentionally permissive — unknown events are
ignored with a 204, not 400, so a stale client running against a
newer server can't trip the dashboard. Same for unknown targets:
they bucket as ``"(unknown)"`` rather than reject.

Read-only mode (``allow_run=False``) still accepts counter writes
— these are UI telemetry, not workflow execution, and the
dashboard is the only thing that POSTs them.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from attune.ops.interaction_counters import EVENTS, InteractionCounters
from attune.ops.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter()


class InteractionEvent(BaseModel):
    """Request body for ``POST /api/telemetry/interaction``.

    ``event`` is the one required field. ``target`` is optional and
    only meaningful for ``pill_click`` and ``scope_picker_change``
    (workflow name) and ``rec_card_click`` (kind: ``next-workflow``
    or ``open-url``). The model accepts anything for ``target`` —
    sanitization happens in :func:`InteractionCounters.record`.
    """

    event: str = Field(..., min_length=1, max_length=64)
    target: str | None = Field(default=None, max_length=256)


def _counters(request: Request) -> InteractionCounters:
    """Return the per-app counters singleton.

    Defensive shim: if the app was constructed before Phase 6.1
    wiring (e.g. an old test fixture), lazily attach a fresh
    counters instance so the endpoints never 500.
    """
    counters = getattr(request.app.state, "interaction_counters", None)
    if counters is None:
        counters = InteractionCounters()
        request.app.state.interaction_counters = counters
    return counters


@router.post("/api/telemetry/interaction")
async def record_interaction(
    payload: InteractionEvent,
    request: Request,
    _client: None = Depends(require_client_token),  # noqa: B008
) -> Response:
    """Increment a UI interaction counter.

    Returns 204 No Content on success AND on unknown events (so a
    stale client doesn't break the dashboard). The body shape is
    validated by pydantic; anything else (charset, length) is
    handled inside the counter store.
    """
    counters = _counters(request)
    recorded = counters.record(payload.event, payload.target)
    if not recorded:
        # Unknown event — log at debug, ignore the request body, and
        # return 204 so the client doesn't retry. This keeps the
        # dashboard resilient to client/server version skew during
        # active development.
        logger.debug(
            "ops.interaction: ignoring unknown event %r (known: %s)",
            payload.event[:64],
            EVENTS,
        )
    return Response(status_code=204)


@router.get("/api/telemetry/interactions")
async def read_interactions(request: Request) -> JSONResponse:
    """Return the full counter snapshot + per-event totals.

    Output shape::

        {
          "totals": {"pill_clicks": int, ...},
          "pill_clicks": {"<workflow>": int, ...},
          "rec_card_clicks": {"<kind>": int, ...},
          "scope_picker_changes": {"<workflow>": int, ...}
        }
    """
    counters = _counters(request)
    snapshot = counters.snapshot()
    return JSONResponse(
        {
            "totals": counters.totals(),
            **snapshot,
        }
    )
