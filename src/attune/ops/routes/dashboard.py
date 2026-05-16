"""All dashboard pages, mounted on a single router."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import data, session_summary

logger = logging.getLogger(__name__)

router = APIRouter()


# Env gate for the Haiku summarizer. Defaults OFF — opt-in for the
# first release per acceptance criterion #5 in requirements.md. When
# off, every session row renders with its heuristic prompt (first
# user message, truncated) and no LLM call is made.
_LLM_GATE_ENV = "ATTUNE_OPS_SESSIONS_LLM"


def _llm_gate_on() -> bool:
    """Return True iff the Haiku-summarizer gate is enabled.

    Accepts the canonical truthy values: ``1``, ``true``, ``yes``,
    ``on`` (case-insensitive). Anything else (including unset)
    keeps the gate off.
    """
    val = os.environ.get(_LLM_GATE_ENV, "").strip().lower()
    return val in ("1", "true", "yes", "on")


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
        # Human-readable project name for the topbar chip. Reads
        # ``[project].name`` from pyproject.toml when available, falls
        # back to the directory basename. Without this, a dashboard
        # launched against a worktree (e.g.
        # ``.claude/worktrees/reverent-brown-937823``) renders the
        # worktree slug as the project name — confusing for users.
        "project_name": data.derive_project_name(cfg.project_root),
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
    # Per-workflow first-paint default scope, auto-derived from
    # features.yaml by exact name match. Each workflow row gets its
    # own ``data-scope-default`` so the JS can restore a
    # workflow-appropriate scope (e.g. ``security-audit`` →
    # ``src/attune/security``) instead of applying one
    # alphabetical-first fallback to every row. Workflows with no
    # matching feature get ``""`` and default to project-wide, which
    # is the safe choice over surfacing an irrelevant scope.
    # localStorage from PR #344 still wins on day 2+; this only
    # affects the empty-localStorage / first-paint case.
    default_scopes = {
        w.name: data.workflow_default_scope(w.name, cfg.project_root) for w in workflows
    }
    return _render(
        request,
        "workflows.html",
        page="workflows",
        workflows=workflows,
        allow_run=cfg.allow_run,
        features=features,
        supports_path=supports_path,
        default_scopes=default_scopes,
        all_code_path=data.ALL_CODE_PATH,
        # Absolute workspace root used by the scope picker to validate
        # localStorage-restored paths. A saved scope from a previous
        # session (possibly a different worktree) that doesn't share
        # this prefix is treated as stale and discarded — prevents
        # the run endpoint from getting a cross-workspace path that
        # will only fail at validation time.
        workspace_root=str(cfg.project_root),
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


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request, compare: int = 0) -> HTMLResponse:
    """Sessions page — recent Claude Code sessions for this project.

    S3a (PR #387): multi-key data layer + summary cache module —
    landed without LLM calls. S3b (this slice): wires the Haiku
    summarizer through, gated on ``ATTUNE_OPS_SESSIONS_LLM``. With
    the gate off (default), every row renders with the heuristic
    starter prompt; with it on, the route walks the cap-limited
    session list, replaces each row's prompt with the Haiku /
    cached summary, and tracks per-page-load spend against a soft
    budget cap (decisions.md Decision 5).

    Compare mode: ``?compare=1`` is a dev-only query parameter that
    renders both the heuristic and Haiku prompts side-by-side for
    pre-launch eyeball validation. No UI affordance for it —
    discoverable only by knowing the URL (decisions.md Decision 9).
    Doesn't bypass the budget cap or redaction.

    Failure modes are silent fall-throughs to the empty state or
    the heuristic prompt: no Claude Code dir, all sessions older
    than 3 days, all JSONLs unreadable, LLM call errored — none
    surface as errors. The point is to be useful on a fresh
    install, not to debug Claude Code's internal state.
    """
    cfg = request.app.state.config
    sessions = data.list_recent_sessions(cfg.project_root, days=3)

    llm_enabled = _llm_gate_on()
    compare_mode = bool(compare) and llm_enabled  # compare requires LLM on
    # Heuristic-only column lives in this dict when compare mode
    # is active. Indexed by session id. None outside compare mode.
    heuristic_by_id: dict[str, str] | None = None
    budget_summary: dict | None = None
    api_key_missing = False

    if llm_enabled:
        budget = session_summary.BudgetTracker()
        if compare_mode:
            # Snapshot the heuristic prompt for each session before
            # replacing the row's prompt with the Haiku summary.
            heuristic_by_id = {s.id: s.starter_prompt for s in sessions}

        # Resolve each session's JSONL path so the orchestrator can
        # compute cache keys. data.list_recent_sessions doesn't
        # surface paths, so re-derive from the encoded-key dirs.
        path_by_id = _resolve_session_jsonl_paths(cfg.project_root, sessions)

        upgraded: list[data.Session] = []
        for sess in sessions:
            jsonl_path = path_by_id.get(sess.id)
            if jsonl_path is None:
                upgraded.append(sess)
                continue
            raw_text = session_summary.extract_summarizable_text(jsonl_path)
            if not raw_text:
                upgraded.append(sess)
                continue
            try:
                summary = session_summary.summarize_for_session(
                    jsonl_path,
                    raw_text,
                    attune_home=cfg.attune_home,
                    budget=budget,
                )
            except session_summary.session_summary_llm.MissingApiKeyError:
                api_key_missing = True
                summary = None
            if summary is None:
                # Heuristic fallback: keep the row's existing
                # heuristic prompt, leave source="heuristic".
                upgraded.append(sess)
                continue
            upgraded.append(
                data.Session(
                    id=sess.id,
                    started_at=sess.started_at,
                    last_activity=sess.last_activity,
                    duration_seconds=sess.duration_seconds,
                    message_count=sess.message_count,
                    starter_prompt=summary.text,
                    source=summary.source,
                )
            )
        sessions = upgraded
        budget_summary = {
            "spend_usd": round(budget.spend_usd, 4),
            "cap_usd": budget.cap_usd,
            "exceeded": budget.spend_usd > budget.cap_usd,
        }

    # Where the sessions live — surfaced in the empty-state so users
    # can ``cat`` the JSONLs directly if they want to inspect more
    # than the page shows. Reuses ``claude_sessions_dir`` so the
    # rendered path matches what ``list_recent_sessions`` reads
    # from disk — naive ``str.replace("/", "-")`` here leaves
    # Windows backslashes and drive-letter colons unencoded.
    # ``as_posix()`` so the rendered path uses ``/`` separators on every
    # platform — on Windows ``str(Path)`` produces native backslashes,
    # which look wrong in the UI and break tests that assert on the
    # POSIX-style path string.
    sessions_dir = (
        "~/" + data.claude_sessions_dir(cfg.project_root).relative_to(Path.home()).as_posix()
    )
    return _render(
        request,
        "sessions.html",
        page="sessions",
        sessions=sessions,
        sessions_dir=sessions_dir,
        llm_enabled=llm_enabled,
        compare_mode=compare_mode,
        heuristic_by_id=heuristic_by_id,
        budget_summary=budget_summary,
        api_key_missing=api_key_missing,
    )


def _resolve_session_jsonl_paths(project_root: Path | str, sessions: list) -> dict[str, Path]:
    """Map each session id to its JSONL file path on disk.

    Walks every encoded-key dir from
    :func:`attune.ops.data.enumerate_project_encoded_keys` and
    matches by filename stem. When the same session id appears
    under multiple keys (rare; same dedup case
    :func:`list_recent_sessions` handles), keeps the
    newest-mtime path to align with the list ordering.

    Returns an empty mapping for any session whose JSONL has
    vanished between listing and resolution — orchestrator will
    treat that as "skip the LLM call" via the empty-text path.
    """
    wanted = {s.id for s in sessions}
    out: dict[str, Path] = {}
    out_mtime: dict[str, float] = {}
    for sessions_dir in data.enumerate_project_encoded_keys(project_root):
        try:
            for jsonl in sessions_dir.glob("*.jsonl"):
                stem = jsonl.stem
                if stem not in wanted:
                    continue
                try:
                    mt = jsonl.stat().st_mtime
                except OSError:
                    continue
                if stem not in out or mt > out_mtime[stem]:
                    out[stem] = jsonl
                    out_mtime[stem] = mt
        except OSError:
            continue
    return out


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
    # In-memory first, then disk fallback. Distinguishing the two is
    # load-bearing on the SSE wiring below: an in-memory Run has a live
    # subscribers set and the executor is still streaming events;
    # a disk-loaded Run is reconstructed without subscribers and has
    # no live executor, so the SSE endpoint would loop indefinitely
    # against it with nothing to stream. We render the log server-side
    # for the disk case and signal the JS to skip EventSource.
    in_memory_run = runner.get(run_id)
    run = in_memory_run if in_memory_run is not None else runner.get_or_load(run_id)
    if run is None:
        logger.info("ops.run_view: run not found: run_id=%s", run_id)
        raise HTTPException(
            status_code=404,
            detail=(
                f"run '{run_id}' not found in memory or on disk. The run "
                "may have been pruned or never persisted."
            ),
        )
    loaded_from_disk = in_memory_run is None
    # SSE is only useful when the executor is live or buffered. For
    # disk-loaded terminal runs we skip the stream entirely; the
    # template renders the full log server-side from ``run.lines``.
    stream_url = "" if loaded_from_disk else f"/runs/{run_id}/stream"
    # Live runs get an empty list — the SSE replay fills the pre on
    # subscribe. Disk-loaded runs ship their captured log inline.
    server_rendered_lines = list(run.lines) if loaded_from_disk else []
    return _render(
        request,
        "run_view.html",
        page="run-view",
        run=run.to_dict(),
        stream_url=stream_url,
        allow_run=request.app.state.config.allow_run,
        server_rendered_lines=server_rendered_lines,
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
                    "last_modified": record.last_modified,
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


def _render_markdown_safe(text: str) -> str:
    """Render markdown to HTML with raw-HTML disabled (XSS-safe).

    Spec files are repo-author-controlled but we still don't accept
    embedded ``<script>`` tags — CommonMark mode (the markdown-it-py
    default) renders raw HTML as escaped text rather than evaluating
    it, which is the safety property we want.
    """
    from markdown_it import MarkdownIt

    md = (
        MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": False})
        .enable("table")
        .enable("strikethrough")
    )
    return md.render(text)


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
        # ``rendered`` holds the HTML-rendered phase bodies (markdown
        # → CommonMark HTML, raw HTML disabled). Template uses these
        # with ``|safe`` so headings, lists, tables, and code fences
        # render as the user expects — replaces the prior raw-text
        # ``<pre>`` dump (P1-2 in the 2026-05-14 QA punch list).
        rendered: dict[str, str] = {}
        for phase in phases:
            if not phase.exists:
                continue
            try:
                text = (spec_dir / phase.file).read_text(encoding="utf-8")
            except OSError:
                # INTENTIONAL: an unreadable phase file is omitted from
                # the rendered map rather than aborting the whole drill-in.
                continue
            try:
                rendered[phase.name] = _render_markdown_safe(text)
            except Exception:  # noqa: BLE001
                # INTENTIONAL: fall back to escaped raw text rather than
                # 500ing the whole page if markdown-it chokes on something
                # unexpected. ``|e`` in the template handles the escape.
                rendered[phase.name] = ""
        return _render(
            request,
            "spec_detail.html",
            page="specs",
            slug=slug,
            root=str(root),
            phases=phases,
            rendered=rendered,
            allow_run=cfg.allow_run,
        )
    raise HTTPException(status_code=404, detail=f"spec '{slug}' not found")
