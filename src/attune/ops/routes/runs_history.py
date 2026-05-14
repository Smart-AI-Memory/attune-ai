"""Read-only API for persisted run records (Phase 3).

Two endpoints:

  * ``GET /api/runs/{workflow}`` → up to 20 newest runs (metadata only).
  * ``GET /api/runs/{workflow}/{run_id}`` → one record including the log.

Both read from ``<attune_home>/ops/runs/<workflow>/<run-id>.json``.
The in-memory ``RunnerService.recent()`` is consulted first so a run
that's still in flight (no JSON on disk yet) is also visible.
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from attune.ops.runner import _list_persisted_runs, _load_run_record

logger = logging.getLogger(__name__)

router = APIRouter()


# Workflow + run-id shape validators. These mirror the regexes in
# ``runner.py`` but are duplicated here so the request-validation
# rejection happens BEFORE any disk lookup. Pre-loaded constants are
# fine — they never change.
_WORKFLOW_NAME_RE = re.compile(r"^[a-z][a-z0-9-]+$")
_RUN_ID_RE = re.compile(r"^[a-f0-9]{1,64}$")


def _strip_lines(record: dict) -> dict:
    """Drop the ``lines`` buffer for list responses to keep payloads small."""
    out = dict(record)
    out.pop("lines", None)
    return out


@router.get("/api/runs/{workflow}")
async def list_runs(workflow: str, request: Request) -> JSONResponse:
    """Return up to 20 newest runs for ``workflow``, newest first.

    Combines in-memory runs (the current + recently-finished, which may
    not be on disk yet) with persisted records. In-memory entries win
    on id collision so an in-flight run's status stays live.
    """
    if not _WORKFLOW_NAME_RE.match(workflow):
        raise HTTPException(status_code=400, detail="invalid workflow name")

    runner = getattr(request.app.state, "runner", None)
    cfg = request.app.state.config

    seen_ids: set[str] = set()
    metadata: list[dict] = []

    # In-memory first — preserves live status / duration for active runs.
    if runner is not None:
        for run in runner.recent(limit=20):
            if run.workflow != workflow:
                continue
            metadata.append(_strip_lines(run.to_record()))
            seen_ids.add(run.id)

    # Disk records second — old runs that aged out of in-memory history.
    runs_dir = cfg.runs_dir
    if runs_dir.is_dir():
        for record in _list_persisted_runs(runs_dir, workflow, limit=20):
            run_id = str(record.get("id") or "")
            if run_id in seen_ids:
                continue
            metadata.append(_strip_lines(record))
            seen_ids.add(run_id)

    metadata.sort(key=lambda r: str(r.get("completed_at") or ""), reverse=True)
    return JSONResponse(content={"workflow": workflow, "runs": metadata[:20]})


@router.get("/api/runs/{workflow}/{run_id}")
async def get_run_record(workflow: str, run_id: str, request: Request) -> JSONResponse:
    """Return one persisted run record (metadata + log).

    Falls back to the in-memory runner if the run isn't on disk yet
    (e.g., still in flight, or completed but pre-persistence in
    read-only mode).
    """
    if not _WORKFLOW_NAME_RE.match(workflow):
        raise HTTPException(status_code=400, detail="invalid workflow name")
    if not _RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail="invalid run id")

    runner = getattr(request.app.state, "runner", None)
    cfg = request.app.state.config

    if runner is not None:
        run = runner.get(run_id)
        if run is not None and run.workflow == workflow:
            return JSONResponse(content=run.to_record())

    record = _load_run_record(cfg.runs_dir, workflow, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    return JSONResponse(content=record)
