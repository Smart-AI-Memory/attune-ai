"""Memory page — read-only view of the Redis-derived index.

C1 + the memory half of C3 in ``docs/specs/ops-dashboard-polish/``
(premise re-validated 2026-07-21 — see decisions.md). Two GET
endpoints, no mutations, no client token needed:

- ``GET /memory`` — family counts + paginated node table
  (``?family=lesson&page=2``). Renders an explanatory empty state
  when Redis is unreachable — the index is optional infrastructure
  and the dashboard must never 500 on its absence.
- ``GET /memory/node`` — one node's hash fields
  (``?key=attune:memory:...``). Keys outside the memory namespace
  404 via the data layer's prefix guard.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import data, memory_data

logger = logging.getLogger(__name__)

router = APIRouter()


def _ctx(request: Request, **extra: object) -> dict[str, object]:
    cfg = request.app.state.config
    return {
        "request": request,
        "page": "memory",
        "project_root": str(cfg.project_root),
        "project_name": data.derive_project_name(cfg.project_root),
        "attune_home": str(cfg.attune_home),
        "current_run": None,
        "family_labels": memory_data.FAMILY_LABELS,
        **extra,
    }


@router.get("/memory", response_class=HTMLResponse)
async def memory_page(request: Request) -> HTMLResponse:
    """Family counts + one page of the node table."""
    family = request.query_params.get("family") or None
    try:
        page = max(1, int(request.query_params.get("page", "1")))
    except ValueError:
        page = 1
    overview = memory_data.read_overview(family=family, page=page)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "memory.html",
        _ctx(request, overview=overview),
    )


@router.get("/memory/node", response_class=HTMLResponse)
async def memory_node(request: Request) -> HTMLResponse:
    """One node's fields, or a not-found state (never a 500)."""
    key = request.query_params.get("key", "")
    fields = memory_data.read_node(key) if key else None
    templates = request.app.state.templates
    response = templates.TemplateResponse(
        request,
        "memory_node.html",
        _ctx(request, node_key=key, fields=fields),
    )
    if fields is None:
        response.status_code = 404
    return response
