"""All dashboard pages, mounted on a single router."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from attune.ops import anthropic_cost, data, workflow_concern

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
    # Anthropic account-spend tiles (Phase 2 of anthropic-cost-integration).
    # Defensive try/except — a fetch crash must not block the dashboard
    # render, so we degrade silently (no tile cluster) on unexpected
    # errors. Categorized failures (no_key, auth_failed, rate_limited,
    # network) come back through cost_error and the template renders
    # the right CTA / notice / fallback per-kind.
    refresh = request.query_params.get("refresh") == "1"
    try:
        cost_summary, cost_error = anthropic_cost.fetch_summary(refresh=refresh)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: defensive degradation; surface in DEBUG logs but
        # never block the home page render on a billing-fetch surprise.
        logger.debug("anthropic_cost.fetch_summary raised", exc_info=True)
        cost_summary, cost_error = None, None
    # Spend anomaly alarm (R6 of usage-signals). Prefers the account-level
    # cost summary already fetched above (it sees CI spend, the surface the
    # $1,200-night lived on); falls back to local usage.jsonl when no admin
    # key is configured. Never raises — degrade to no panel on a surprise.
    try:
        spend = data.build_spend_alarm(cfg, cost_summary)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: the alarm is a best-effort signal; never block the
        # home render on an aggregation surprise.
        logger.debug("data.build_spend_alarm raised", exc_info=True)
        spend = None
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
        cost_summary=cost_summary,
        cost_error=cost_error,
        spend=spend,
    )


@router.get("/workflows", response_class=HTMLResponse)
async def workflows_page(request: Request) -> HTMLResponse:
    workflows = data.list_workflows()
    cfg = request.app.state.config
    features = data.list_features(cfg.project_root)
    # Server-side first-paint of the discovery-sweep chip counts.
    # JS refreshes these via /api/workflows/discovery-sweep/chips
    # when the user changes the scope picker; the initial render
    # uses each row's default scope (or the project root) so chips
    # appear immediately without a fetch round-trip.
    sweep_default_scope = data.workflow_default_scope("discovery-sweep", cfg.project_root)
    sweep_scope_path = sweep_default_scope or str(cfg.project_root)
    sweep_chips = data.read_sweep_chip_counts(sweep_scope_path, cfg)
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
    # A2 of docs/specs/ops-workflows-page-refinement/. Per-row concern
    # bucket + per-bucket counts derived from the workflow_concern
    # module (PR #552 — pure logic, no I/O). The template's chip
    # toolbar (A3a) renders one chip per bucket with these counts;
    # each row gets a `concern-pill` badge keyed off concerns[name].
    workflow_names = [w.name for w in workflows]
    concerns = {name: workflow_concern.derive_concern(name) for name in workflow_names}
    bucket_counts = workflow_concern.concern_counts(workflow_names)
    return _render(
        request,
        "workflows.html",
        page="workflows",
        workflows=workflows,
        allow_run=cfg.allow_run,
        features=features,
        supports_path=supports_path,
        default_scopes=default_scopes,
        concerns=concerns,
        bucket_counts=bucket_counts,
        all_concerns=workflow_concern.ALL_CONCERNS,
        all_code_path=data.ALL_CODE_PATH,
        tier_label=data.TIER_LABEL,
        tier_tooltip=data.TIER_TOOLTIP,
        sweep_chips=sweep_chips,
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
    # Phase 6.1 of ops-runner-tier2 — surface in-memory UI interaction
    # counters alongside the persisted workflow telemetry. These are
    # per-process tallies (reset on dashboard restart); the template
    # labels the section accordingly so users don't confuse them with
    # the disk-backed numbers above.
    counters = getattr(request.app.state, "interaction_counters", None)
    interaction_totals = counters.totals() if counters is not None else {}
    interaction_top = {
        "pill_clicks": counters.top("pill_click", limit=10) if counters else [],
        "rec_card_clicks": counters.top("rec_card_click", limit=10) if counters else [],
        "scope_picker_changes": (counters.top("scope_picker_change", limit=10) if counters else []),
    }
    # Short-term memory injection cost — read from the memory hooks'
    # local event log. Reports measured cost (tokens injected), not a
    # savings estimate; the template captions it accordingly.
    memory_summary = data.read_memory_summary(cfg.memory_events_path)
    # Labeled benefit estimate — carries its own honesty caption; the
    # template renders it verbatim so this never reads as measured savings.
    memory_signal = data.estimate_intervention_signal(cfg.memory_events_path)
    # Noise side — findings surfaced then dropped as noise.
    memory_feedback = data.estimate_feedback_signal(cfg.memory_events_path)
    # US-6 three-panel receipt: reach + freshness + spend TOGETHER on
    # one page. Reach reads the tracked snapshots dir; freshness reads
    # usage.jsonl's mtime; spend reuses the shipped D13 alarm (local
    # source here — the account-level fetch stays on the home route).
    reach = data.read_reach_panel(cfg)
    freshness = data.read_usage_freshness(cfg)
    try:
        spend = data.build_spend_alarm(cfg, None)
    except Exception:  # noqa: BLE001
        # INTENTIONAL: the alarm is a best-effort signal; never block
        # the telemetry page on it (mirrors the home route).
        logger.debug("data.build_spend_alarm raised", exc_info=True)
        spend = None
    return _render(
        request,
        "telemetry.html",
        page="telemetry",
        telemetry=summary,
        interaction_totals=interaction_totals,
        interaction_top=interaction_top,
        memory_summary=memory_summary,
        memory_signal=memory_signal,
        memory_feedback=memory_feedback,
        reach=reach,
        freshness=freshness,
        spend=spend,
    )


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request) -> HTMLResponse:
    cfg = request.app.state.config
    snapshot = data.env_health(cfg)
    return _render(request, "health.html", page="health", snapshot=snapshot)


# ---------------------------------------------------------------------------
# Help — see docs/specs/ops-help-page/
# ---------------------------------------------------------------------------


# Kinds grouped by intent — used by the home page's "Browse by
# what you need" cards. Same shape as help_data.INTENT_GROUPS but
# duplicated here for template-side rendering convenience.
_HELP_INTENTS = (
    {
        "id": "do",
        "icon": "⚡",
        "title": "Do something",
        "kinds": ("task", "quickstart"),
    },
    {
        "id": "solve",
        "icon": "🔧",
        "title": "Solve a problem",
        "kinds": ("troubleshooting", "error", "faq"),
    },
    {
        "id": "understand",
        "icon": "💡",
        "title": "Understand",
        "kinds": ("concept",),
    },
    {
        "id": "lookup",
        "icon": "📖",
        "title": "Look it up",
        "kinds": ("reference",),
    },
)


def _count_articles_for_kinds(features, kinds: tuple[str, ...]) -> int:
    """Total templates across features that match the intent's kinds."""
    out = 0
    for f in features:
        for k in kinds:
            if k in f.kinds:
                out += 1
    return out


@router.get("/help", response_class=HTMLResponse)
async def help_home_page(request: Request) -> HTMLResponse:
    """Help home — user-first browse + search entry point."""
    from attune.ops import help_data

    cfg = request.app.state.config
    features = help_data.list_features(cfg)
    featured = help_data.featured_topics(cfg)
    recent = help_data.recently_regenerated(cfg, limit=5)
    intents = [
        dict(intent, count=_count_articles_for_kinds(features, intent["kinds"]))
        for intent in _HELP_INTENTS
    ]
    total_templates = sum(len(f.kinds) for f in features)
    stale_count = sum(f.stale_count for f in features)
    incomplete_count = sum(1 for f in features if not f.is_complete)
    return _render(
        request,
        "help.html",
        page="help",
        features=features,
        featured=featured,
        recent=recent,
        intents=intents,
        total_features=len(features),
        total_templates=total_templates,
        stale_count=stale_count,
        incomplete_count=incomplete_count,
    )


@router.get("/help/search", response_class=HTMLResponse)
async def help_search_page(request: Request, q: str = "") -> HTMLResponse:
    """Help search results page."""
    from attune.ops import help_data

    cfg = request.app.state.config
    hits = help_data.search(cfg, q, limit=20)
    return _render(request, "help_search.html", page="help", q=q, hits=hits)


@router.get("/help/admin", response_class=HTMLResponse)
async def help_admin_page(request: Request) -> HTMLResponse:
    """Admin tools — coverage gaps + stale templates."""
    from attune.ops import help_data

    cfg = request.app.state.config
    report = help_data.coverage_gaps(cfg)
    return _render(request, "help_admin.html", page="help", report=report)


@router.get("/help/{feature}/{kind}", response_class=HTMLResponse)
async def help_template_page(request: Request, feature: str, kind: str) -> HTMLResponse:
    """One template — markdown-rendered."""
    from fastapi import HTTPException

    from attune.ops import help_data

    if not help_data._safe_slug(feature) or not help_data._safe_slug(kind):
        raise HTTPException(status_code=400, detail="invalid slug")
    cfg = request.app.state.config
    rec = help_data.get_template(cfg, feature, kind)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"template not found: {feature}/{kind}")
    # Sibling kinds for the in-page nav
    features = {f.name: f for f in help_data.list_features(cfg)}
    feat = features.get(feature)
    sibling_kinds = list(feat.kinds) if feat else []
    rendered_body = _render_markdown_safe(rec.body)
    return _render(
        request,
        "help_template.html",
        page="help",
        record=rec,
        sibling_kinds=sibling_kinds,
        rendered_body=rendered_body,
    )


@router.get("/help/{feature}", response_class=HTMLResponse)
async def help_feature_page(request: Request, feature: str) -> HTMLResponse:
    """Feature index — list of available kinds, click to read."""
    from fastapi import HTTPException

    from attune.ops import help_data

    if not help_data._safe_slug(feature):
        raise HTTPException(status_code=400, detail="invalid feature slug")
    cfg = request.app.state.config
    features = {f.name: f for f in help_data.list_features(cfg)}
    feat = features.get(feature)
    if feat is None:
        raise HTTPException(status_code=404, detail=f"feature not found: {feature}")
    return _render(request, "help_feature.html", page="help", feature_obj=feat)


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request) -> HTMLResponse:
    """Sessions page — recent Claude Code sessions for this project.

    S3b: wires the Haiku summarizer + on-disk cache + redaction
    behind the existing data layer. Each row's ``starter_prompt``
    is the Haiku-or-cached summary when available, falling back
    to the heuristic (first user prompt, truncated) when the LLM
    is disabled, the budget is breached, or any failure path
    fires. The ``source`` field on each :class:`Session` (one of
    ``heuristic | haiku | cached``) tells the user which lane
    produced the text.

    Query params:

    - ``?compare=1`` — dev mode. Runs the full enrichment AND
      preserves the heuristic alongside, rendering both columns
      side-by-side. No UI affordance (discoverable only by URL).
      Same budget + redaction + caching applies.

    Failure modes are silent fall-throughs to the empty state: no
    Claude Code dir, all sessions older than 3 days, all JSONLs
    unreadable — none surface as errors. The point is to be useful
    on a fresh install, not to debug Claude Code's internal state.

    S4 will add the resume-most-recent card; S5 marks the live
    session.
    """
    from attune.ops.routes.sessions import enrich_with_summaries
    from attune.ops.session_summarizer import llm_enabled, new_budget

    cfg = request.app.state.config
    compare_mode = request.query_params.get("compare") == "1"

    # Both branches below call the SYNCHRONOUS Anthropic SDK
    # (``anthropic.Anthropic(...).messages.create()``) inside a
    # per-session loop. Running them directly inside this async route
    # blocks the uvicorn event loop for the duration of the Haiku
    # batch (~0.5–2s per session × N sessions), freezing every other
    # request. Defer to a thread; the ``anthropic`` SDK is documented
    # thread-safe and ``summarize_session``'s sync API is preserved
    # for tests and other paths.
    import asyncio

    if compare_mode:
        # Compare mode renders both columns. Keep the heuristic
        # version (paths-included call) and run the enrichment
        # alongside on the same path list so the rows align.
        pairs = data.list_recent_sessions_with_paths(cfg.project_root, days=3)
        heuristic_sessions = [s for s, _ in pairs]
        budget = new_budget()
        from attune.ops.routes.sessions import _enrich_sessions

        haiku_sessions, over_budget = await asyncio.to_thread(
            _enrich_sessions, pairs, attune_home=cfg.attune_home, budget=budget
        )
        sessions = heuristic_sessions
        compare_columns = [
            {"label": "Heuristic", "sessions": heuristic_sessions},
            {"label": "Haiku", "sessions": haiku_sessions},
        ]
    else:
        sessions, over_budget = await asyncio.to_thread(
            enrich_with_summaries, cfg.project_root, cfg.attune_home
        )
        compare_columns = None

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
        compare_mode=compare_mode,
        compare_columns=compare_columns,
        over_budget=over_budget,
        llm_enabled=llm_enabled(),
    )


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
    # Existing diagnoses for this run (advanced-debugging-plugin T5) —
    # drives the "diagnosed" chip and suppresses the diagnose button.
    # Best-effort: a broken diagnosis store never breaks the run view.
    try:
        from attune.diagnosis import records_for_run

        diagnosis_ids = [r.diagnosis_id for r in records_for_run(run_id)]
    except Exception:  # noqa: BLE001 — page render must survive store faults
        logger.debug("ops.run_view: diagnosis lookup failed", exc_info=True)
        diagnosis_ids = []
    return _render(
        request,
        "run_view.html",
        page="run-view",
        run=run.to_dict(),
        stream_url=stream_url,
        allow_run=request.app.state.config.allow_run,
        server_rendered_lines=server_rendered_lines,
        diagnosis_ids=diagnosis_ids,
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
                    "lifecycle": record.lifecycle,
                    "stage": record.stage,
                    "next_phase": record.next_phase,
                    "next_action": record.next_action,
                    "next_phase_status": record.next_phase_status,
                    "waived_phases": list(record.waived_phases),
                }
            )
    # Bucket counts for the chip filter row. All 6 keys are always present
    # so the template can render chips with `0` counts for empty buckets
    # (better UX than missing chips that pop in/out as data shifts).
    bucket_counts = dict.fromkeys(
        ("active", "approved-not-shipped", "complete", "paused", "parked", "stale", "draft"), 0
    )
    for s in specs:
        bucket_counts[s["lifecycle"]] = bucket_counts.get(s["lifecycle"], 0) + 1
    # GitHub repo for the "View linked PRs" kebab action (A3b).
    # Reuses the resolver from completion_candidates (handles SSH +
    # HTTPS + git protocol URLs). None if not a GitHub-hosted git repo;
    # the template renders the action as disabled in that case.
    from attune.ops.completion_candidates import _resolve_host_repo

    github_repo = _resolve_host_repo(cfg.project_root)
    # URL params for initial chip / sort / search state (A3c). The JS
    # owns the live state machine; the server's job is to make the
    # first paint already match what the URL says, so a shared link
    # like `?bucket=stale&q=rag` renders correctly without a flash of
    # default state followed by JS re-render.
    initial_buckets, initial_sort, initial_query = _parse_specs_url_state(request.query_params)
    # Gate-verdict badges (spec-lifecycle-gates UI phase): newest
    # machine receipt per slug from the RR-1 ledger; {} until the
    # gates ship, and the column renders identically without it.
    from attune.ops.spec_lifecycle import read_gate_verdicts

    gate_verdicts = read_gate_verdicts(cfg.attune_home / "ops" / "gates" / "verdicts.jsonl")
    return _render(
        request,
        "specs.html",
        page="specs",
        specs=specs,
        gate_verdicts=gate_verdicts,
        roots=[str(r) for r in roots],
        allow_run=cfg.allow_run,
        specs_candidates_enabled=cfg.specs_candidates_enabled,
        bucket_counts=bucket_counts,
        github_repo=github_repo,
        initial_buckets=initial_buckets,
        initial_sort=initial_sort,
        initial_query=initial_query,
    )


# A3c — URL param parsing helpers. Module-level so tests can import
# without spinning up the full FastAPI app.

_VALID_BUCKETS: frozenset[str] = frozenset(
    {"active", "approved-not-shipped", "complete", "paused", "parked", "stale", "draft"}
)
_VALID_SORTS: frozenset[str] = frozenset({"recent", "alpha", "oldest"})
# Defaults match the JS DEFAULT_BUCKETS in specs_refined.js exactly:
# all chips on except Complete (R1.3).
_DEFAULT_BUCKETS: tuple[str, ...] = (
    "active",
    "approved-not-shipped",
    "paused",
    "parked",
    "stale",
    "draft",
)


def _parse_specs_url_state(
    query_params,
) -> tuple[list[str], str, str]:
    """Parse `?bucket=`, `?sort=`, `?q=` URL params for the Specs page.

    Args:
        query_params: Starlette ``QueryParams`` (request.query_params).

    Returns:
        ``(initial_buckets, initial_sort, initial_query)``. Invalid
        values fall back to defaults silently rather than rejecting
        the request — the URL is a UI affordance, not a strict
        contract, and a malformed share link should still render the
        page (with default state) rather than 400.

    The default bucket set matches the JS ``DEFAULT_BUCKETS`` exactly
    so the first paint and the JS-controlled state align.
    """
    # bucket=active,paused → ["active", "paused"]. Missing param → defaults.
    raw_buckets = query_params.get("bucket")
    if raw_buckets is None:
        buckets = list(_DEFAULT_BUCKETS)
    else:
        candidates = [b.strip() for b in raw_buckets.split(",") if b.strip()]
        buckets = [b for b in candidates if b in _VALID_BUCKETS]
        # If filtering left nothing valid, fall back to defaults so the
        # page isn't stuck in an empty state from a malformed share link.
        if not buckets:
            buckets = list(_DEFAULT_BUCKETS)

    # sort=alpha → "alpha". Invalid → "recent" (default).
    raw_sort = query_params.get("sort", "recent")
    initial_sort = raw_sort if raw_sort in _VALID_SORTS else "recent"

    # q=substring → "substring". Cap at 200 chars to bound rendering
    # cost; the JS already does substring filtering so longer queries
    # don't unlock new behavior, just bloat the URL.
    raw_query = query_params.get("q", "")
    initial_query = raw_query[:200] if raw_query else ""

    return buckets, initial_sort, initial_query


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
