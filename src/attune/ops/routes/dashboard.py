"""All dashboard pages, mounted on a single router."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import data

router = APIRouter()


def _ctx(request: Request, page: str, **extra) -> dict:
    cfg = request.app.state.config
    return {
        "request": request,
        "page": page,
        "project_root": str(cfg.project_root),
        "attune_home": str(cfg.attune_home),
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
    return _render(
        request,
        "workflows.html",
        page="workflows",
        workflows=workflows,
        allow_run=cfg.allow_run,
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
