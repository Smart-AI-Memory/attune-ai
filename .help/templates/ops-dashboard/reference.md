---
type: reference
name: ops-dashboard-reference
feature: ops-dashboard
depth: reference
generated_at: 2026-06-02T10:56:02.708475+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Ops Dashboard reference

Use this reference to look up every public class, function, dataclass field, and module constant in `attune ops` — the local operations dashboard with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CostFetchError` | Categorized failure for cost-report fetch. | `src/attune/ops/anthropic_cost.py` |
| `CostSummary` | Account-level cost data from the Anthropic admin cost-report. | `src/attune/ops/anthropic_cost.py` |
| `Candidate` | One completion-candidate spec returned by the detector. | `src/attune/ops/completion_candidates.py` |
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | Aggregated telemetry: request counts, costs, savings, and per-workflow/day breakdowns. | `src/attune/ops/data.py` |
| `WorkflowEntry` | One registered workflow — name, description, stage count, and tier map. | `src/attune/ops/data.py` |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. | `src/attune/ops/data.py` |
| `Feature` | One feature from `.help/features.yaml` for the scope picker. | `src/attune/ops/data.py` |
| `Session` | One Claude Code session — what surfaces on the dashboard's /sessions page. | `src/attune/ops/data.py` |
| `FamilyVersion` | Installed version record for one package in the attune family. | `src/attune/ops/data.py` |
| `DailyCost` | One day's cost for the home-page sparkline. | `src/attune/ops/data.py` |
| `HomeKpis` | Summary numbers shown above the fold on the home page. | `src/attune/ops/data.py` |
| `SweepChipCounts` | Per-bucket counts loaded from a persisted discovery-sweep result. | `src/attune/ops/data.py` |
| `DismissEntry` | One dismissed candidate's persisted state. | `src/attune/ops/dismiss_store.py` |
| `TemplateRecord` | One template file. | `src/attune/ops/help_data.py` |
| `FeatureSummary` | One feature — name + which kinds exist. | `src/attune/ops/help_data.py` |
| `SearchHit` | One ranked hit from a search query. | `src/attune/ops/help_data.py` |
| `GapsReport` | Coverage-gap signals — incomplete sets + stale templates. | `src/attune/ops/help_data.py` |
| `HelpRegenJob` | One regen invocation — status, captured stdout, exit code. | `src/attune/ops/help_regen.py` |
| `HelpRegenRunner` | Owns the regen-job history + active subprocess. | `src/attune/ops/help_regen.py` |
| `HelpRegenBusyError` | Raised when a regen job is requested while one is already running. | `src/attune/ops/help_regen.py` |
| `InteractionCounters` | Process-lifetime counters for dashboard UI interactions. | `src/attune/ops/interaction_counters.py` |
| `TrustedHostMiddleware` | Rejects requests whose `Host` header isn't on the allowlist. | `src/attune/ops/middleware.py` |
| `JournalEntry` | One pending-writes journal entry. | `src/attune/ops/pending_writes.py` |
| `InteractionEvent` | Request body for `POST /api/telemetry/interaction`. | `src/attune/ops/routes/interaction_counters.py` |
| `SpecPhase` | One phase file's status snapshot. | `src/attune/ops/routes/specs.py` |
| `SpecRecord` | One spec's summary — directory + status of each phase file present. | `src/attune/ops/routes/specs.py` |
| `RunnerBusyError` | Raised when a run is already pending/running. | `src/attune/ops/runner.py` |
| `Run` | Single workflow execution + its broadcast state. | `src/attune/ops/runner.py` |
| `RunnerService` | Owns the run history + concurrency lock. | `src/attune/ops/runner.py` |
| `RedactionResult` | Outcome of a redaction pass. | `src/attune/ops/session_redaction.py` |
| `SummaryResult` | One Haiku-or-cache result, ready to slot into a `Session`. | `src/attune/ops/session_summarizer.py` |
| `Budget` | Mutable spend ledger for one page-load summarization loop. | `src/attune/ops/session_summarizer.py` |
| `CacheKey` | Stable key that invalidates a cached summary when the source moves. | `src/attune/ops/session_summary_cache.py` |
| `CachedSummary` | One persisted session summary plus the metadata to validate it. | `src/attune/ops/session_summary_cache.py` |

## Dataclass fields

### `CostFetchError`

| Field | Type | Default |
|-------|------|---------|
| `kind` | `CostFetchErrorKind` | — |
| `message` | `str` | — |

### `CostSummary`

| Field | Type | Default |
|-------|------|---------|
| `today_usd` | `float` | — |
| `seven_day_usd` | `float` | — |
| `month_to_date_usd` | `float` | — |
| `thirty_day_usd` | `float` | — |
| `by_day` | `list[tuple[date, float]]` | — |
| `by_model` | `list[tuple[str, float]]` | — |
| `by_cost_type` | `list[tuple[str, float]]` | — |
| `fetched_at` | `datetime` | — |
| `source` | `Literal['live', 'cached']` | — |

### `Candidate`

| Field | Type | Default |
|-------|------|---------|
| `slug` | `str` | — |
| `path` | `str` | — |
| `current_status` | `str` | — |
| `evidence` | `list[str]` | — |
| `snapshot_hash` | `str` | — |

### `Config`

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
| `specs_candidates_enabled` | `bool` | `False` |

#### `Config` properties

| Property | Type | Description |
|----------|------|-------------|
| `telemetry_path` | `Path` | Path to the telemetry data file. |
| `runs_dir` | `Path` | Disk root for persisted ops runs. May not exist until first write. |
| `memory_dir` | `Path` | Path to the memory directory. |
| `sessions_dir` | `Path` | Path to the sessions directory. |
| `bulletin_dir` | `Path` | Directory for the multi-actor bulletin's active log + archive. |

### `TelemetrySummary`

| Field | Type | Default |
|-------|------|---------|
| `total_requests` | `int` | — |
| `total_cost` | `float` | — |
| `total_savings` | `float` | — |
| `by_workflow` | `list[tuple[str, int, float]]` | — |
| `by_day` | `list[tuple[str, int, float]]` | — |
| `last_event_at` | `str | None` | — |

### `WorkflowEntry`

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `stages` | `int` | — |
| `tier_map` | `dict[str, str]` | — |

### `PathArgSpec`

| Field | Type | Default |
|-------|------|---------|
| `kwarg` | `str` | — |
| `required` | `bool` | `False` |

### `Feature`

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `path` | `str | None` | — |
| `tags` | `tuple[str, ...]` | `()` |

### `Session`

| Field | Type | Default |
|-------|------|---------|
| `id` | `str` | — |
| `started_at` | `str` | — |
| `last_activity` | `str` | — |
| `duration_seconds` | `float` | — |
| `message_count` | `int` | — |
| `starter_prompt` | `str` | — |
| `source` | `str` | `'heuristic'` |

### `FamilyVersion`

| Field | Type | Default |
|-------|------|---------|
| `package` | `str` | — |
| `version` | `str | None` | — |
| `source` | `str` | — |

## Functions

### Cost reporting (`src/attune/ops/anthropic_cost.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `clear_cache` | — | `None` | Empty the in-memory cache. Test-only convenience. |
| `load_admin_key` | — | `str | None` | Return the admin API key, or `None` if unavailable. |
| `fetch_summary` | `*, refresh: bool = False` | `tuple[CostSummary | None, CostFetchError | None]` | Return the current cost summary or a categorized error. |

### CLI (`src/attune/ops/cli.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `add_subparser` | `subparsers: argparse._SubParsersAction` | `None` | Register the `ops` subparser on the main attune CLI parser. |
| `cmd_ops` | `args: argparse.Namespace` | `int` | Run the dashboard server (blocking). Returns `0`. |
| `main` | — | `int` | Standalone entry point: `python -m attune.ops`. |

### Completion candidates (`src/attune/ops/completion_candidates.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `clear_cache` | — | `None` | Reset the in-memory caches. Test helper. |
| `detect_candidates` | `config: Config, *, now: float | None = None` | `list[Candidate]` | Return all completion candidates across the configured spec roots. |

### Config (`src/attune/ops/config.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `attune_home` | — | `Path` | Resolve the user's attune home dir (env override → ~/.attune). |
| `build_config` | `project_root: Path | None = None, *, host: str = '127.0.0.1', port: int = 8765, allow_run: bool = False, specs_roots: tuple[Path, ...] | None = None, trusted_hosts: tuple[str, ...] | None = None, runs_retention_days: int = 30, specs_candidates_enabled: bool = False` | `Config` | Build a `Config` from inputs and environment defaults. |

### Data helpers (`src/attune/ops/data.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_features` | `project_root: Path | str` | `list[Feature]` | Return features parsed from `<project_root>/.help/features.yaml`. |
| `first_feature` | `project_root: Path | str` | `Feature | None` | Return the alphabetically-first feature with a renderable scope. |
| `workflow_default_scope` | `workflow_name: str, project_root: Path | str` | `str` | Return the default scope for one workflow on first paint. |
| `derive_project_name` | `project_root: Path | str` | `str` | Return a human-readable project name for the dashboard header. |
| `claude_sessions_dir` | `project_root: Path | str` | `Path` | Return the canonical directory Claude Code stores sessions for this project in. |
| `enumerate_project_encoded_keys` | `project_root: Path | str` | `list[Path]` | Return all `~/.claude/projects/` dirs belonging to this logical project. |
| `list_recent_sessions_with_paths` | `project_root: Path | str, *, days: int = 3, limit: int | None = DEFAULT_SESSION_LIST_CAP, now: datetime | None = None, parser: Callable[[Path], Session | None] | None = None` | `list[tuple[Session, Path]]` | Same as `list_recent_sessions` but also returns each session's source path. |
| `list_recent_sessions` | `project_root: Path | str, *, days: int = 3, limit: int | None = DEFAULT_SESSION_LIST_CAP, now: datetime | None = None, parser: Callable[[Path], Session | None] | None = None` | `list[Session]` | Return `Session` records for this project's last `days` of activity. |
| `home_kpis` | `summary: TelemetrySummary, *, today: date | None = None` | `HomeKpis` | Derive home-page KPIs from a telemetry summary. |
| `sparkline_points` | `values: list[float], *, width: int = 240, height: int = 40` | `str` | Render values as an SVG `polyline` `points` string. |
| `read_telemetry_summary` | `config: Config, *, recent_days: int = 7, today: date | None = None` | `TelemetrySummary` | Aggregate `usage.jsonl` into a UI-friendly summary. |
| `read_sweep_chip_counts` | `scope_path: str, config: Config` | `SweepChipCounts` | Read the latest persisted sweep result for `scope_path` and tally chips. |
| `list_workflows` | — | `list[WorkflowEntry]` | Return the registered workflow catalog. Empty if the registry is unavailable. |
| `family_versions` | — | `list[FamilyVersion]` | Resolve installed versions for every related attune package. |
| `env_health` | `config: Config` | `dict[str, Any]` | Lightweight environment snapshot for the Health page. |

### Dismiss store (`src/attune/ops/dismiss_store.py`)

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `store_path` | `config: Config` | `Path` | Return the absolute
