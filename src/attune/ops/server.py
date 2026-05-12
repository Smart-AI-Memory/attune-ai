"""FastAPI app factory for attune ops."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from attune import __version__
from attune.ops.config import Config
from attune.ops.routes import dashboard
from attune.ops.routes import runner as runner_routes
from attune.ops.routes import specs as specs_routes
from attune.ops.runner import RunnerService


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
