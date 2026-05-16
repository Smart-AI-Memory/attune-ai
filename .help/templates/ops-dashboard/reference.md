---
type: reference
name: ops-dashboard-reference
feature: ops-dashboard
depth: reference
generated_at: 2026-05-16T06:19:45.796093+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Ops Dashboard reference

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

Run via `python -m attune.ops` or the `attune ops` CLI subcommand. The public surface exported from `attune.ops` is `create_app`, `build_config`, and `Config`.

## Classes

| Class | Description |
|-------|-------------|
| `Config` | Where attune ops reads project + attune state from. |
| `TelemetrySummary` | Aggregated telemetry totals and breakdowns for the dashboard. |
| `WorkflowEntry` | One entry in the registered workflow catalog. |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. |
| `Feature` | One feature from `.help/features.yaml` for the scope picker. |
| `Session` | One Claude Code session — what surfaces on the dashboard's `/sessions` page. |
| `FamilyVersion` | Installed version record for one related attune package. |
| `DailyCost` | One day's cost for the home-page sparkline. |
| `HomeKpis` | Summary numbers shown above the fold on the home page. |
| `TrustedHostMiddleware` | Reject requests whose `Host` header isn't on the allowlist. |

### `Config` fields

| Field | Type | Default |
|-------|------|---------|
| `project_root` | `Path` | — |
| `attune_home` | `Path` | — |
| `host` | `str` | `'127.0.0.1'` |
| `port` | `int` | `8765` |
| `allow_run` | `bool` | `False` |
| `specs_roots` | `tuple[Path, ...]` | `()` |
| `trusted_hosts` | `tuple[str, ...]` | `()` |
| `runs_retention_days` | `int` | `30` |

### `Config` properties

| Property | Type | Description |
|----------|------|-------------|
| `telemetry_path` | `Path` | Path to the telemetry data file. |
| `runs_dir` | `Path` | Disk root for persisted ops runs. May not exist until first write. |
| `memory_dir` | `Path` | Path to the attune memory directory. |
| `sessions_dir` | `Path` | Path to the sessions directory. |

### `TelemetrySummary` fields

| Field | Type | Default |
|-------|------|---------|
| `total_requests` | `int` | — |
| `total_cost` | `float` | — |
| `total_savings` | `float` | — |
| `by_workflow` | `list[tuple[str, int, float]]` | — |
| `by_day` | `list[tuple[str, int, float]]` | — |
| `last_event_at` | `str | None` | — |

### `WorkflowEntry` fields

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `stages` | `int` | — |
| `tier_map` | `dict[str, str]` | — |

### `PathArgSpec` fields

| Field | Type | Default |
|-------|------|---------|
| `kwarg` | `str` | — |
| `required` | `bool` | `False` |

### `Feature` fields

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `path` | `str | None` | — |
| `tags` | `tuple[str, ...]` | `()` |

### `Session` fields

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `started_at` | `str` | — |
| `last_activity` | `str` | — |
| `duration_seconds` | `float` | — |
| `message_count` | `int` | — |
| `starter_prompt` | `str` | — |
| `source` | `str` | `'heuristic'` |

### `FamilyVersion` fields

| Field | Type | Default |
|-------|------|---------|
| `package` | `str` | — |
| `version` | `str | None` | — |
| `source` | `str` | — |

### `DailyCost` fields

| Field | Type | Default |
|-------|------|---------|
| `day` | `str` | — |
| `events` | `int` | — |
| `cost` | `float` | — |

### `HomeKpis` fields

| Field | Type | Default |
|-------|------|---------|
| `today_events` | `int` | — |
| `today_cost` | `float` | — |
| `seven_day_cost` | `float` | — |
| `seven_day_savings` | `float` | — |
| `sparkline` | `list[DailyCost]` | — |

### `TrustedHostMiddleware` methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `app: object, *, allowed_hosts: Iterable[str]` | `None` | Construct the middleware with an explicit host allowlist. |
| `dispatch` | `request: Request, call_next: Callable[[Request], Awaitable[Response]]` | `Response` | Enforce the allowlist; pass through or reject each request. |

## Functions

### Configuration

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `attune_home` | — | `Path` | Resolve the user's attune home dir (env override → `~/.attune`). |
| `build_config` | `project_root: Path \| None = None, *, host: str = '127.0.0.1', port: int = 8765, allow_run: bool = False, specs_roots: tuple[Path, ...] \| None = None, trusted_hosts: tuple[str, ...] \| None = None, runs_retention_days: int = 30` | `Config` | Build a `Config` from inputs and environment defaults. |

### CLI and entry points

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `add_subparser` | `subparsers: argparse._SubParsersAction` | `None` | Register the `ops` subparser on the main attune CLI parser. |
| `cmd_ops` | `args: argparse.Namespace` | `int` | Run the dashboard server (blocking). Returns `0` on clean exit. |
| `main` | — | `int` | Standalone entry point: `python -m attune.ops`. |

### App factory

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | `config: Config, *, runner: RunnerService \| None = None` | `FastAPI` | Build the FastAPI app, wiring config + templates into request state. |

### Feature and workflow data

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_features` | `project_root: Path \| str` | `list[Feature]` | Return features parsed from `<project_root>/.help/features.yaml`. |
| `first_feature` | `project_root: Path \| str` | `Feature \| None` | Return the alphabetically-first feature with a renderable scope. |
| `workflow_default_scope` | `workflow_name: str, project_root: Path \| str` | `str` | Return the default scope for one workflow on first paint. Returns `''` when no default applies. |
| `list_workflows` | — | `list[WorkflowEntry]` | Return the registered workflow catalog. Empty if the registry is unavailable. |
| `derive_project_name` | `project_root: Path \| str` | `str` | Return a human-readable project name for the dashboard header. |

### Session data

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `claude_sessions_dir` | `project_root: Path \| str` | `Path` | Return the canonical directory Claude Code stores sessions for this project in. |
| `enumerate_project_encoded_keys` | `project_root: Path \| str` | `list[Path]` | Return all `~/.claude/projects/` dirs belonging to this logical project. |
| `list_recent_sessions` | `project_root: Path \| str, *, days: int = 3, limit: int \| None = DEFAULT_SESSION_LIST_CAP, now: datetime \| None = None, parser: Callable[[Path], Session \| None] \| None = None` | `list[Session]` | Return `Session` records for this project's last `days` of activity. |
| `list_recent_sessions_with_paths` | `project_root: Path \| str, *, days: int = 3, limit: int \| None = DEFAULT_SESSION_LIST_CAP, now: datetime \| None = None, parser: Callable[[Path], Session \| None] \| None = None` | `list[tuple[Session, Path]]` | Same as `list_recent_sessions` but also returns each session's source path. |

### Telemetry and KPIs

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `read_telemetry_summary` | `config: Config, *, recent_days: int = 7` | `TelemetrySummary` | Aggregate `usage.jsonl` into a UI-friendly summary. |
| `home_kpis` | `summary: TelemetrySummary, *, today: date \| None = None` | `HomeKpis` | Derive home-page KPIs from a telemetry summary. |
| `sparkline_points` | `values: list[float], *, width: int = 240, height: int = 40` | `str` | Render values as an SVG `polyline` `points` string. |
| `family_versions` | — | `list[FamilyVersion]` | Resolve installed versions for every related attune package. |
| `env_health` | `config: Config` | `dict[str, Any]` | Lightweight environment snapshot for the Health page. |

### Middleware

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `compute_allowlist` | `host: str, port: int, extras: Iterable[str] = ()` | `set[str]` | Compute the default + user-supplied Host allowlist. |

### Dashboard routes

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `home` | `request: Request` | `HTMLResponse` | Render the dashboard home page. |
| `workflows_page` | `request: Request` | `HTMLResponse` | Render the workflows listing page. |
| `telemetry_page` | `request: Request` | `HTMLResponse` | Render the telemetry page. |
| `health_page` | `request: Request` | `HTMLResponse` | Render the health page. |
| `sessions_page` | `request: Request` | `HTMLResponse` | Sessions page — recent Claude Code sessions for this project. |
| `run_view_page` | `run_id: str, request: Request` | `HTMLResponse` | Full-page view for one workflow run. |
| `specs_page` | `request: Request` | `HTMLResponse` | Specs tab — federated listing of all specs across configured roots. |
| `spec_detail_page` | `slug: str, request: Request` | `HTMLResponse` | Drill-in for a single spec: show every phase file's content (read-only). |

### Runner routes

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `start_run` | `name: str, request: Request` | `JSONResponse` | Start a named workflow run. |
| `get_run` | `run_id: str, request: Request` | `JSONResponse` | Return current state for one run. |
| `stream_run` | `run_id: str, request: Request` | `StreamingResponse` | Stream live SSE log output for one run. |

### Run history routes

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_runs` | `workflow: str, request: Request` | `JSONResponse` | Return up to 20 newest runs for `workflow`, newest first. |
| `get_run_record` | `workflow: str, run_id: str, request: Request` | `JSONResponse` | Return one persisted run record (metadata + log). |

### Sessions route helpers

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `enrich_with_summaries` | `project_root, attune_home, *, days: int = 3, limit: int \| None = data.DEFAULT_SESSION_LIST_CAP, budget: session_summarizer.Budget \| None = None` | `tuple[list[data.Session], bool]` | Attach Haiku-or-cached summaries to a batch of sessions; used by both the JSON route and the HTML page. |
| `list_sessions` | `request: Request` | `dict[str, Any]` | `GET /api/sessions` — JSON listing of recent sessions. |

### Spec routes

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_specs` | `request: Request` | `dict` | Federated listing across all configured spec roots. |
| `get_spec` | `slug: str, request: Request` | `dict` | Return phase-file contents for one spec. |
| `update_phase_status` | `slug: str, phase: str, request: Request, body: dict[str, Any] = Body(...)` | `dict[str, Any]` | Rewrite the `**Status**` line in the named phase file. |

### Sweep results

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_sweep_result` | `scope_hash: str, request: Request` | `JSONResponse` | Return the latest sweep result for a scope-hash, or 404. |
| `is_persistence_enabled` | — | `bool` | True when `ATTUNE_OPS_SWEEP_RESULTS` is set to a non-empty value. |
| `results_dir` | `config: Config` | `Path` | Return `<attune_home>/ops/sweep-results/` (created if missing). |
| `scope_hash` | `scope_path: str` | `str` | Hash a scope path to a fixed-length hex identifier. |
| `parse_lines` | `lines: list[str]` | `dict[str, Any] \| None` | Parse a captured stdout buffer into the final SweepResult JSON. |
| `persist_result` | `scope_path: str, sweep_result: dict[str, Any], config: Config` | `Path` | Atomically write `sweep_result` to `<results_dir>/<hash>.json`. |
| `read_result` | `digest: str, config: Config` | `dict[str, Any] \| None` | Read a previously-persisted result by its scope-hash digest. |
| `persist_from_lines` | `scope_path: str, lines: list[str], config: Config` | `Path \| None` | Parse captured stdout lines and persist the result for `scope_path`. |
| `watch_and_persist` | `run: Run, config: Config` | `None` | Subscribe to a discovery-sweep run; persist its result on success. |

### Runner utilities

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `echo_command_builder` | `workflow: str` | `Sequence[str]` | Test helper: produce a portable subprocess that prints two lines and exits 0. |
| `prune_old_runs` |
