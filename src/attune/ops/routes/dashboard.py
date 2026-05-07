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


@router.get("/memory", response_class=HTMLResponse)
async def memory_page(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    entries = data.list_memory_topics(cfg)
    return _render(request, "memory.html", page="memory", entries=entries)


@router.get("/releases", response_class=HTMLResponse)
async def releases_page(request: Request) -> HTMLResponse:
    versions = data.family_versions()
    return _render(request, "releases.html", page="releases", versions=versions)


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    snapshot = data.env_health(cfg)
    return _render(request, "health.html", page="health", snapshot=snapshot)
