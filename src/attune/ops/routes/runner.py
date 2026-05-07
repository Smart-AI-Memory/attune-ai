"""HTTP routes for workflow execution + SSE log streaming."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from attune.ops.runner import RunnerBusyError, RunnerService

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


@router.post("/workflows/{name}/run")
async def start_run(name: str, request: Request) -> JSONResponse:
    _ensure_allowed(request)
    svc = _service(request)
    try:
        run = await svc.start(name)
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
