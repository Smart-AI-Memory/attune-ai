"""Library-health snapshot page — ``/health/library``.

Phase E of ``docs/specs/ops-dashboard-polish/`` (see decisions.md for
the three ratified decisions this route implements). Renders the
latest deterministic metrics snapshot collected by
:mod:`attune.ops.health_snapshot`; the page itself never blocks on
live collection — it reads ``latest.json`` and, when stale, kicks a
background-thread refresh that a follow-up poll or page reload
picks up.

Named distinctly from the pre-existing ``/health`` route
(``dashboard.py``'s ``health_page`` — Python/platform/state-file
presence) to avoid conflating two unrelated concepts under one URL;
see decisions.md's "Naming note" for the full rationale.

Three endpoints:

- ``GET /health/library`` — HTML page. Renders the latest snapshot
  (or an empty state if none exists yet) and kicks a background
  refresh when the snapshot is stale (>12h, see
  :data:`attune.ops.health_snapshot.DEFAULT_STALE_AFTER_HOURS`).
- ``POST /health/library/refresh`` — client-token gated. Starts a
  background refresh unconditionally (subject to the single-
  in-flight-job guard); returns immediately.
- ``GET /api/health/library/status`` — JSON poll target for the
  in-page JS to detect when a background refresh has finished.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)

from attune.ops import data, health_snapshot
from attune.ops.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter()


def _page_context(request: Request, **extra: object) -> dict[str, object]:
    cfg = request.app.state.config
    return {
        "request": request,
        "page": "health-library",
        "project_root": str(cfg.project_root),
        "project_name": data.derive_project_name(cfg.project_root),
        "attune_home": str(cfg.attune_home),
        "current_run": None,
        **extra,
    }


def _maybe_kick_refresh(request: Request, snapshot: dict[str, object] | None) -> None:
    """Start a background refresh if the snapshot is stale.

    ``HealthRefreshRunner.start`` is itself a no-op when a refresh is
    already in flight, so calling this on every GET is safe — it
    won't pile up duplicate jobs.
    """
    if not health_snapshot.is_stale(snapshot):
        return
    cfg = request.app.state.config
    request.app.state.health_refresh.start(cfg.project_root, cfg.attune_home)


@router.get("/health", response_class=HTMLResponse)
async def health_library_page(request: Request) -> HTMLResponse:
    """Render the latest library-health snapshot, refreshing in the background if stale."""
    cfg = request.app.state.config
    snapshot = health_snapshot.read_latest(cfg.attune_home)
    stale = health_snapshot.is_stale(snapshot)
    _maybe_kick_refresh(request, snapshot)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "health_library.html",
        _page_context(
            request,
            snapshot=snapshot,
            stale=stale,
            refreshing=request.app.state.health_refresh.running,
            stale_after_hours=health_snapshot.DEFAULT_STALE_AFTER_HOURS,
            latest_report=health_snapshot.latest_llm_report(cfg.project_root),
            env=data.env_health(cfg),
        ),
    )


@router.post("/health/library/refresh")
async def health_library_refresh(
    request: Request,
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    """Start a background snapshot refresh. Token-gated (mutating route)."""
    cfg = request.app.state.config
    runner = request.app.state.health_refresh
    started = runner.start(cfg.project_root, cfg.attune_home)
    return JSONResponse(content={"started": started, "running": runner.running})


@router.get("/api/health/library/status")
async def health_library_status(request: Request) -> JSONResponse:
    """Poll target for the page's "refresh in progress" indicator."""
    cfg = request.app.state.config
    runner = request.app.state.health_refresh
    snapshot = health_snapshot.read_latest(cfg.attune_home)
    return JSONResponse(
        content={
            "running": runner.running,
            "collected_at": snapshot.get("collected_at") if snapshot else None,
        }
    )


@router.get("/health/library")
async def health_library_redirect() -> RedirectResponse:
    """Permanent redirect — the Library Health page merged into /health
    (chair-ruled 2026-07-21). Old bookmarks and links keep working."""
    return RedirectResponse(url="/health", status_code=301)


_REPORT_NAME_RE = re.compile(r"^library-health-[A-Za-z0-9._-]+\.md$")


@router.get("/docs/reports/{name}", response_class=PlainTextResponse)
async def serve_llm_report(request: Request, name: str) -> PlainTextResponse:
    """Serve a library-health narrative report as plain text.

    Closes the one broken link the 2026-07-21 link-QA crawl found:
    the Health page links ``/{{ latest_report }}`` but nothing served
    ``/docs/reports/...``. Read-only, strictly validated: the name
    must match the report pattern AND resolve inside
    ``<project_root>/docs/reports`` (no traversal), else 404.
    """
    if not _REPORT_NAME_RE.match(name):
        raise HTTPException(status_code=404)
    cfg = request.app.state.config
    reports_dir = (Path(cfg.project_root) / "docs" / "reports").resolve()
    target = (reports_dir / name).resolve()
    if not str(target).startswith(str(reports_dir) + os.sep) or not target.is_file():
        raise HTTPException(status_code=404)
    return PlainTextResponse(target.read_text(encoding="utf-8"))
