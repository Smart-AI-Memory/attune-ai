"""All dashboard pages, mounted on a single router."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import data

logger = logging.getLogger(__name__)

router = APIRouter()


def _ctx(request: Request, page: str, **extra) -> dict:
    cfg = request.app.state.config
    runner = getattr(request.app.state, "runner", None)
    current_run = None
    if runner is not None:
        active = runner.current
        if active is not None:
            current_run = {
                "id": active.id,
                "workflow": active.workflow,
                "status": active.status,
            }
    return {
        "request": request,
        "page": page,
        "project_root": str(cfg.project_root),
        "attune_home": str(cfg.attune_home),
        "current_run": current_run,
        **extra,
    }


def _render(request: Request, template: str, page: str, **extra) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request, template, _ctx(request, page=page, **extra))


@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    summary = data.read_telemetry_summary(cfg)
    workflows = data.list_workflows()
    versions = data.family_versions()
    kpis = data.home_kpis(summary)
    sparkline = data.sparkline_points([d.cost for d in kpis.sparkline])
    runner = getattr(request.app.state, "runner", None)
    recent_runs = [r.to_dict() for r in runner.recent(limit=5)] if runner else []
    attune_ai = next((v for v in versions if v.package == "attune-ai"), None)
    return _render(
        request,
        "home.html",
        page="home",
        telemetry=summary,
        workflow_count=len(workflows),
        versions=versions,
        kpis=kpis,
        sparkline=sparkline,
        recent_runs=recent_runs,
        attune_ai=attune_ai,
    )


@router.get("/workflows", response_class=HTMLResponse)
async def workflows_page(request: Request) -> HTMLResponse:
    workflows = data.list_workflows()
    cfg = request.app.state.config
    features = data.list_features(cfg.project_root)
    # supports_path[name] is True iff the workflow has a PATH_ARG_REGISTRY
    # entry. The template uses this to render the scope picker vs an
    # "n/a" span. Future-proofed: a new workflow without a registry
    # entry shows as n/a until the registry is updated.
    supports_path = {w.name: w.name in data.PATH_ARG_REGISTRY for w in workflows}
    # Alphabetically-first feature path is the primary picker fallback
    # when localStorage is empty. When no path-bearing feature exists,
    # the JS falls through to ALL_CODE_PATH.
    first = data.first_feature(cfg.project_root)
    first_feature_path = first.path if first else ""
    return _render(
        request,
        "workflows.html",
        page="workflows",
        workflows=workflows,
        allow_run=cfg.allow_run,
        features=features,
        supports_path=supports_path,
        first_feature_path=first_feature_path,
        all_code_path=data.ALL_CODE_PATH,
    )


@router.get("/telemetry", response_class=HTMLResponse)
async def telemetry_page(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    summary = data.read_telemetry_summary(cfg, recent_days=14)
    return _render(request, "telemetry.html", page="telemetry", telemetry=summary)


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    snapshot = data.env_health(cfg)
    return _render(request, "health.html", page="health", snapshot=snapshot)


@router.get("/runs/{run_id}/view", response_class=HTMLResponse)
async def run_view_page(run_id: str, request: Request) -> HTMLResponse:
    """Full-page view for one workflow run.

    URL-bound: refreshing the page re-attaches to the existing run's SSE
    stream (the runner replays the buffered log for any new subscriber),
    so the output survives a browser refresh. Also gives the log full
    viewport width instead of being constrained to the workflows-table
    row width.

    Slug-safety: run_id is server-allocated (UUID hex from Python's
    `uuid.uuid4`). Anything that isn't `[a-f0-9-]` is rejected as a
    bad-input 400 before we look it up.
    """
    # Reject anything that doesn't look like a UUID hex. Prevents path
    # traversal via `..%2F..%2Fetc...` and similar.
    import re as _re

    from fastapi import (
        HTTPException,
    )  # noqa: F811 — local re-import keeps the module-top imports lean

    if not _re.match(r"^[A-Za-z0-9_-]{1,64}$", run_id):
        # Log at WARN since this is either a bug in the caller or a
        # probe. Truncate the offending input to keep the log line bounded.
        logger.warning("ops.run_view: invalid run_id input: %r", run_id[:64])
        raise HTTPException(status_code=400, detail="invalid run_id")

    runner = getattr(request.app.state, "runner", None)
    if runner is None:
        raise HTTPException(status_code=503, detail="runner unavailable")
    run = runner.get(run_id)
    if run is None:
        logger.info("ops.run_view: run not found: run_id=%s", run_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"run '{run_id}' not found. The runner keeps the last 20 runs "
                "in memory; older runs are pruned when the server restarts."
            ),
        )
    return _render(
        request,
        "run_view.html",
        page="run-view",
        run=run.to_dict(),
        stream_url=f"/runs/{run_id}/stream",
        allow_run=request.app.state.config.allow_run,
    )


@router.get("/specs", response_class=HTMLResponse)
async def specs_page(request: Request) -> HTMLResponse:
    """Specs tab — federated listing of all specs across configured roots.

    Reuses the same root resolution + scanning logic as the JSON API so the
    HTML view and the API can't drift.
    """
    from dataclasses import asdict

    from attune.ops.routes.specs import _list_specs_in_root, _resolved_roots

    cfg = request.app.state.config
    roots = _resolved_roots(cfg)
    specs = []
    for root in roots:
        for record in _list_specs_in_root(root):
            specs.append(
                {
                    "slug": record.slug,
                    "root": record.root,
                    "path": record.path,
                    "phases": [asdict(p) for p in record.phases],
                }
            )
    return _render(
        request,
        "specs.html",
        page="specs",
        specs=specs,
        roots=[str(r) for r in roots],
        allow_run=cfg.allow_run,
    )


@router.get("/specs/{slug}", response_class=HTMLResponse)
async def spec_detail_page(slug: str, request: Request) -> HTMLResponse:
    """Drill-in for a single spec: show every phase file's content (read-only)."""
    from fastapi import HTTPException

    from attune.ops.routes.specs import _resolved_roots, _scan_spec_dir

    # Slug-safety: directory name shape only, no path separators or traversal.
    if "/" in slug or ".." in slug or "\\" in slug:
        raise HTTPException(status_code=400, detail="invalid slug")

    cfg = request.app.state.config
    roots = _resolved_roots(cfg)
    for root in roots:
        spec_dir = root / slug
        if not spec_dir.is_dir():
            continue
        phases = _scan_spec_dir(spec_dir)
        contents: dict[str, str] = {}
        for phase in phases:
            if not phase.exists:
                continue
            try:
                contents[phase.name] = (spec_dir / phase.file).read_text(encoding="utf-8")
            except OSError:
                # INTENTIONAL: an unreadable phase file is omitted from the
                # contents map rather than aborting the whole drill-in.
                continue
        return _render(
            request,
            "spec_detail.html",
            page="specs",
            slug=slug,
            root=str(root),
            phases=phases,
            contents=contents,
            allow_run=cfg.allow_run,
        )
    raise HTTPException(status_code=404, detail=f"spec '{slug}' not found")
