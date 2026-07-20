"""HTTP routes for workflow execution + SSE log streaming."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from attune.ops import data
from attune.ops.runner import RunnerBusyError, RunnerService
from attune.ops.security import require_client_token
from attune.security.path_validation import _validate_file_path


def _absolutize_scope(scope: str, project_root: Path) -> str:
    """Resolve a user-supplied scope path against ``project_root``.

    The dashboard sends scopes as repo-relative strings (e.g.
    ``"src/attune/agents"``) derived from ``features.yaml`` via
    ``data.workflow_default_scope``. The downstream validator does
    ``Path(scope).resolve()``, which resolves a relative path against
    ``Path.cwd()`` — NOT against ``project_root``. When the dashboard
    is launched from a directory other than its ``--project-root``
    (common in worktree setups), cwd and project_root diverge and
    every scope-bearing workflow run is rejected as "outside allowed
    directory".

    Anchoring relative scopes here, before validation, decouples scope
    resolution from process cwd. Absolute scopes are passed through
    unchanged so the validator can still reject anything that escapes
    ``project_root``.
    """
    p = Path(scope)
    if p.is_absolute():
        return scope
    return str(project_root / p)


logger = logging.getLogger(__name__)

router = APIRouter()


def _service(request: Request) -> RunnerService:
    svc: RunnerService | None = getattr(request.app.state, "runner", None)
    if svc is None:
        raise HTTPException(status_code=500, detail="runner service unavailable")
    return svc


def _ensure_allowed(request: Request) -> None:
    if not request.app.state.config.allow_run:
        raise HTTPException(
            status_code=403,
            detail="workflow execution is disabled; restart attune ops with --allow-run",
        )


async def _read_run_body(request: Request) -> tuple[str | None, str | None]:
    """Parse the optional ``{"path": ..., "trigger": ...}`` run body.

    Returns ``(path, trigger)``; an empty body yields ``(None, None)``.
    Treats an empty-string path the same as omitted so the picker's
    "Project-wide" option doesn't have to send anything special.
    ``trigger`` is the run's provenance stamp (run-record-corpus RC-3):
    ``"attune-rec"`` for recommendation-launched runs, ``"manual"`` or
    omitted otherwise; any other value is a 400 (the contract is
    explicit at the API edge even though the subprocess-side resolver
    is junk-tolerant).
    """
    body_bytes = await request.body()
    if not body_bytes:
        return None, None
    try:
        raw = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON body") from exc
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="body must be a JSON object")
    raw_path = raw.get("path")
    if raw_path == "":
        raw_path = None
    if raw_path is not None and not isinstance(raw_path, str):
        raise HTTPException(status_code=400, detail="path must be a string")
    raw_trigger = raw.get("trigger")
    if raw_trigger == "":
        raw_trigger = None
    if raw_trigger is not None and raw_trigger not in ("manual", "attune-rec", "attune-heal"):
        raise HTTPException(
            status_code=400,
            detail="trigger must be 'manual', 'attune-rec', or 'attune-heal'",
        )
    return raw_path, raw_trigger


@router.post("/workflows/{name}/run")
async def start_run(
    name: str,
    request: Request,
    _client: None = Depends(require_client_token),  # noqa: B008
) -> JSONResponse:
    _ensure_allowed(request)
    svc = _service(request)

    scope, trigger = await _read_run_body(request)
    if scope is not None:
        # Reject scope for workflows that don't accept a path arg. The
        # registry is the source of truth for path-arg support; a
        # workflow absent from the registry is treated as no-path.
        if name not in data.PATH_ARG_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"workflow '{name}' does not accept a path argument",
            )
        cfg = request.app.state.config
        # Anchor relative scopes to project_root BEFORE validation. The
        # validator's Path.resolve() uses cwd for relative paths, which
        # breaks when the dashboard's cwd != --project-root (common in
        # worktree launches). See _absolutize_scope docstring.
        scope = _absolutize_scope(scope, cfg.project_root)
        try:
            validated = _validate_file_path(scope, allowed_dir=str(cfg.project_root))
        except ValueError as exc:
            logger.warning("ops.run: rejected scope path %r: %s", scope[:200], exc)
            raise HTTPException(status_code=400, detail=f"invalid path: {exc}") from exc
        scope = str(validated)

    try:
        run = await svc.start(name, path=scope, trigger=trigger)
    except RunnerBusyError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": "runner busy", "current_run_id": exc.current_run_id},
        ) from exc
    return JSONResponse(
        status_code=201,
        content={
            "run_id": run.id,
            "stream_url": f"/runs/{run.id}/stream",
            "status_url": f"/runs/{run.id}",
        },
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str, request: Request) -> JSONResponse:
    svc = _service(request)
    run = svc.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return JSONResponse(content=run.to_dict())


@router.get("/runs/{run_id}/report")
async def get_run_report(run_id: str, request: Request) -> JSONResponse:
    """Structured ``WorkflowReport`` for a run, plus its summary markdown.

    Returns ``{"report": <dict>, "markdown": <str>}`` when the run
    carried a serialized report over the run-meta side-channel; 404
    when the run is unknown or produced no structured report (the run
    view treats that as "no panel", keeping unmigrated workflows
    working unchanged). The markdown is rendered server-side by the
    canonical renderer so the dashboard never reimplements report
    formatting — it only converts the constrained markdown subset to
    HTML. Workflow-result-formatting T6; disk-loaded runs are served
    via ``get_or_load`` so the panel survives a daemon restart.
    """
    svc = _service(request)
    run = svc.get_or_load(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run.report is None:
        raise HTTPException(status_code=404, detail="run has no structured report")

    from attune.config import resolve_show_cost
    from attune.voice.report_renderer import render_safe
    from attune.workflows.output import WorkflowReport

    try:
        report = WorkflowReport.from_dict(run.report)
    except (TypeError, ValueError) as exc:
        logger.warning("ops.report: malformed report for run %s: %s", run_id, exc)
        raise HTTPException(status_code=404, detail="run report is malformed") from exc
    markdown = render_safe(report, disclosure="summary", show_cost=resolve_show_cost())
    return JSONResponse(content={"report": run.report, "markdown": markdown})


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    svc = _service(request)
    run = svc.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_source() -> AsyncIterator[bytes]:
        async for kind, payload in run.subscribe():
            yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n".encode()

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
