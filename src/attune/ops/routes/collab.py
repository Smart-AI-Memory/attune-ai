"""Collaboration inbox — display, deep-link, never promote.

Roundtable-ruled (q-ops-memory-multi-llm-pages-001, issue #1613):
GET-only. Promotion is in-session by design (R4) — the page renders
the exact ``/roundtable promote <thread>`` command instead of any
action button.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import collab_data, data

logger = logging.getLogger(__name__)

router = APIRouter()


def _ctx(request: Request, **extra: object) -> dict[str, object]:
    cfg = request.app.state.config
    return {
        "request": request,
        "page": "collab",
        "project_root": str(cfg.project_root),
        "project_name": data.derive_project_name(cfg.project_root),
        "attune_home": str(cfg.attune_home),
        "current_run": None,
        **extra,
    }


@router.get("/collab", response_class=HTMLResponse)
async def collab_page(request: Request) -> HTMLResponse:
    """Action-required-first inbox; sources degrade independently."""
    inbox = collab_data.read_inbox(request.app.state.config.project_root)
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "collab.html", _ctx(request, inbox=inbox))


@router.get("/collab/thread", response_class=HTMLResponse)
async def collab_thread(request: Request) -> HTMLResponse:
    """One thread's messages, read-only (never a 500)."""
    thread = request.query_params.get("id", "")
    messages = collab_data.read_thread(thread) if thread else None
    templates = request.app.state.templates
    response = templates.TemplateResponse(
        request,
        "collab_thread.html",
        _ctx(request, thread=thread, messages=messages),
    )
    if messages is None:
        response.status_code = 404
    return response
