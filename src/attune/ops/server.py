"""FastAPI app factory for attune ops."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from attune import __version__
from attune.bulletin import FileBulletinBackend
from attune.ops import sweep_results as sweep_results_mod
from attune.ops.config import Config
from attune.ops.interaction_counters import InteractionCounters
from attune.ops.routes import bulletin as bulletin_routes
from attune.ops.routes import curator as curator_routes
from attune.ops.routes import dashboard
from attune.ops.routes import health_library as health_library_routes
from attune.ops.routes import help as help_routes
from attune.ops.routes import interaction_counters as interaction_counters_routes
from attune.ops.routes import memory as memory_routes
from attune.ops.routes import pending_writes as pending_writes_routes
from attune.ops.routes import runner as runner_routes
from attune.ops.routes import runs_history as runs_history_routes
from attune.ops.routes import session as session_routes
from attune.ops.routes import specs as specs_routes
from attune.ops.routes import sweep_results as sweep_results_routes
from attune.ops.runner import RunnerService, prune_old_runs
from attune.ops.security import current_session_token
from attune.ops.sweep_results_watcher import watch_and_persist


def _package_dir(name: str) -> Path:
    """Return absolute path to a package data subdirectory."""
    return Path(str(files("attune.ops").joinpath(name)))


def _build_default_runner(config: Config) -> RunnerService:
    """Construct the runner with persistence enabled when runs are allowed.

    Read-only mode (``allow_run=False``) disables disk writes entirely —
    a read-only dashboard should not modify the user's ``~/.attune``.
    The bulletin is only wired in writeable mode for the same reason.
    """
    if not config.allow_run:
        return RunnerService(project_root=config.project_root)
    bulletin = FileBulletinBackend(config.bulletin_dir)
    return RunnerService(
        persistence_dir=config.runs_dir,
        project_root=config.project_root,
        bulletin=bulletin,
        actor_kind="dashboard",
    )


def create_app(config: Config, *, runner: RunnerService | None = None) -> FastAPI:
    """Build the FastAPI app, wiring config + templates into request state."""
    # Sweep stale persisted runs before serving any traffic. Bounded by
    # `runs_retention_days` (CLI flag), `0` disables the sweep entirely.
    if config.allow_run and config.runs_retention_days > 0:
        try:
            prune_old_runs(config.runs_dir, days=config.runs_retention_days)
        except OSError:
            # INTENTIONAL: best-effort sweep; never block startup on a
            # filesystem hiccup. The helper itself swallows per-file
            # errors; this only catches the outer iterdir failure.
            pass

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
    # Per-process client token injected into every page (base.html meta
    # tag); the page echoes it as X-Attune-Client on mutating fetches.
    # See attune.ops.security / docs/specs/ops-mutating-endpoint-auth/.
    templates.env.globals["client_token"] = current_session_token()
    templates.env.globals["nav_items"] = [
        ("/", "Home"),
        ("/workflows", "Workflows"),
        ("/curator", "Briefing"),
        ("/specs", "Specs"),
        ("/memory", "Memory"),
        ("/telemetry", "Telemetry"),
        ("/health", "Health"),
        ("/help", "Help"),
    ]

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.state.config = config
    app.state.templates = templates
    app.state.runner = runner if runner is not None else _build_default_runner(config)
    # Phase 6.1 of ops-runner-tier2 — process-lifetime UI interaction
    # counters (pill clicks, recommendation-card clicks, scope-picker
    # changes). In-memory only; resets on restart. See
    # ``interaction_counters.py`` for bucket layout.
    app.state.interaction_counters = InteractionCounters()
    # Help-corpus regen runner — wraps attune-author subprocess
    # invocations. Single concurrent job, one history per server
    # instance. See docs/specs/ops-help-page/.
    from attune.ops.help_regen import HelpRegenRunner

    app.state.help_regen = HelpRegenRunner()
    # Library-health snapshot background refresh — single in-flight
    # job, mirrors help_regen's shape but runs in a plain thread
    # (the collector is blocking-subprocess/HTTP, not asyncio-native).
    # See docs/specs/ops-dashboard-polish/decisions.md Phase E.
    from attune.ops.health_snapshot import HealthRefreshRunner

    app.state.health_refresh = HealthRefreshRunner()

    app.include_router(session_routes.router)
    app.include_router(dashboard.router)
    app.include_router(health_library_routes.router)
    app.include_router(runner_routes.router)
    app.include_router(runs_history_routes.router)
    app.include_router(specs_routes.router)
    app.include_router(sweep_results_routes.router)
    app.include_router(interaction_counters_routes.router)
    app.include_router(memory_routes.router)
    app.include_router(pending_writes_routes.router)
    app.include_router(bulletin_routes.router)
    app.include_router(curator_routes.router)
    app.include_router(help_routes.router)

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
        # API paths get JSON so client-side error parsing works; HTML
        # pages get the styled 404 template. ``getattr`` shields against
        # the case where ``exc`` is a Starlette HTTPException (which has
        # ``.detail``) vs a bare 404 (which doesn't).
        detail = getattr(exc, "detail", None) or "not found"
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"detail": detail})
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
