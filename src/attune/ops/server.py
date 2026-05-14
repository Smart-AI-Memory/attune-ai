"""FastAPI app factory for attune ops."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from attune import __version__
from attune.ops import sweep_results as sweep_results_mod
from attune.ops.config import Config
from attune.ops.routes import dashboard
from attune.ops.routes import runner as runner_routes
from attune.ops.routes import specs as specs_routes
from attune.ops.routes import sweep_results as sweep_results_routes
from attune.ops.runner import RunnerService
from attune.ops.sweep_results_watcher import watch_and_persist


def _package_dir(name: str) -> Path:
    """Return absolute path to a package data subdirectory."""
    return Path(str(files("attune.ops").joinpath(name)))


def create_app(config: Config, *, runner: RunnerService | None = None) -> FastAPI:
    """Build the FastAPI app, wiring config + templates into request state."""
    app = FastAPI(
        title="attune ops",
        version=__version__,
        description="Operations dashboard for attune-ai",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # Host header allowlist — DNS-rebinding defense. MUST be the first
    # middleware so untrusted requests get rejected before any routing.
    # See docs/specs/ops-security-hardening/.
    from attune.ops.middleware import TrustedHostMiddleware, compute_allowlist

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=compute_allowlist(
            host=config.host,
            port=config.port,
            extras=config.trusted_hosts,
        ),
    )

    templates_dir = _package_dir("templates")
    static_dir = _package_dir("static")

    templates = Jinja2Templates(directory=str(templates_dir))
    templates.env.globals["attune_version"] = __version__
    templates.env.globals["nav_items"] = [
        ("/", "Home"),
        ("/workflows", "Workflows"),
        ("/specs", "Specs"),
        ("/telemetry", "Telemetry"),
        ("/health", "Health"),
    ]

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.state.config = config
    app.state.templates = templates
    app.state.runner = runner if runner is not None else RunnerService()

    app.include_router(dashboard.router)
    app.include_router(runner_routes.router)
    app.include_router(specs_routes.router)
    app.include_router(sweep_results_routes.router)

    # Phase 2B of discovery-sweep-ops-integration: when sweep-result
    # persistence is enabled, wrap the runner's start() so each
    # discovery-sweep run gets a watcher task that persists the
    # captured ATTUNE_DS stream to ~/.attune/ops/sweep-results/.
    # Wrap goes here (not in runner.py) to avoid touching the
    # conflict-prone runner module.
    if sweep_results_mod.is_persistence_enabled():
        _original_start = app.state.runner.start

        async def _start_with_sweep_watcher(workflow, *args, **kwargs):
            import asyncio

            run = await _original_start(workflow, *args, **kwargs)
            if workflow == "discovery-sweep":
                asyncio.create_task(watch_and_persist(run, config))
            return run

        app.state.runner.start = _start_with_sweep_watcher  # type: ignore[method-assign]

    @app.get("/api/info", response_class=JSONResponse)
    async def info(request: Request):
        cfg: Config = request.app.state.config
        return {
            "version": __version__,
            "project_root": str(cfg.project_root),
            "attune_home": str(cfg.attune_home),
        }

    @app.exception_handler(404)
    async def not_found(request: Request, exc):  # type: ignore[no-untyped-def]
        templates = request.app.state.templates
        cfg: Config = request.app.state.config
        return HTMLResponse(
            templates.get_template("404.html").render(
                {
                    "request": request,
                    "page": "404",
                    "path": request.url.path,
                    "project_root": str(cfg.project_root),
                    "attune_home": str(cfg.attune_home),
                }
            ),
            status_code=404,
        )

    return app
