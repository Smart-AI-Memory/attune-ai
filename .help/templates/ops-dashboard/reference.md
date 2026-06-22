---
type: reference
name: ops-dashboard-reference
feature: ops-dashboard
depth: reference
generated_at: 2026-06-22T10:00:48.764701+00:00
source_hash: dd650b4658efc1f6876bf6f2701d846e9091228187573660cdcfc10ab83fa6c2
status: generated
---

# Ops Dashboard reference

Run and monitor the attune workflow OS from a local web dashboard. The dashboard exposes a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. Start it with `attune ops` or `python -m attune.ops`.

## Classes

| Class | Description |
|-------|-------------|
| `CostFetchError` | Categorized failure for a cost-report fetch. |
| `CostSummary` | Account-level cost data from the Anthropic admin cost-report. |
| `Candidate` | One completion-candidate spec returned by the detector. |
| `Config` | Project and attune-state configuration that `attune ops` reads at startup. |
| `TelemetrySummary` | Aggregated telemetry — request counts, costs, savings, and per-workflow breakdowns. |
| `WorkflowEntry` | One entry in the registered workflow catalog. |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. |
| `Feature` | One feature from `.help/features.yaml` for the scope picker. |
| `Session` | One Claude Code session surfaced on the dashboard's `/sessions` page. |
| `FamilyVersion` | Package name, version, and resolution source for one attune family member. |
| `DailyCost` | One day's cost for the home-page sparkline. |
| `HomeKpis` | Summary numbers shown above the fold on the home page. |
| `SpendAlarm` | Daily API-spend anomaly verdict with ceiling-approach gauge for the dashboard (R6). |
| `SweepChipCounts` | Per-bucket counts loaded from a persisted discovery-sweep result. |
| `DismissEntry` | One dismissed candidate's persisted state. |
| `TemplateRecord` | One template file in the help corpus. |
| `FeatureSummary` | One feature — name plus which template kinds exist for it. |
| `SearchHit` | One ranked hit from a help-corpus search query. |
| `GapsReport` | Coverage-gap signals — incomplete sets and stale templates. |
| `HelpRegenJob` | One regen invocation — status, captured stdout, and exit code. |
| `HelpRegenRunner` | Owns the regen-job history and active subprocess. |
| `HelpRegenBusyError` | Raised when a regen job is requested while one is already running. |
| `InteractionCounters` | Process-lifetime counters for dashboard UI interactions. |
| `TrustedHostMiddleware` | Rejects requests whose `Host` header is not on the allowlist. |
| `JournalEntry` | One pending-writes journal entry. |
| `InteractionEvent` | Request body for `POST /api/telemetry/interaction`. |
| `SpecPhase` | One phase file's status snapshot. |
| `SpecRecord` | One spec's summary — directory plus the status of each phase file present. |
| `RunnerBusyError` | Raised when a run is already pending or running. |
| `Run` | Single workflow execution and its broadcast state. |
| `RunnerService` | Owns the run history and concurrency lock. |
| `RedactionResult` | Outcome of a redaction pass. |
| `SummaryResult` | One Haiku-or-cache result, ready to slot into a `Session`. |
| `Budget` | Mutable spend ledger for one page-load summarization loop. |
| `CacheKey` | Stable key that invalidates a cached summary when the source moves. |
| `CachedSummary` | One persisted session summary plus the metadata needed to validate it. |

---

### `CostFetchError` fields

| Field | Type |
|-------|------|
| `kind` | `CostFetchErrorKind` |
| `message` | `str` |

---

### `CostSummary` fields

| Field | Type |
|-------|------|
| `today_usd` | `float` |
| `seven_day_usd` | `float` |
| `month_to_date_usd` | `float` |
| `thirty_day_usd` | `float` |
| `by_day` | `list[tuple[date, float]]` |
| `by_model` | `list[tuple[str, float]]` |
| `by_cost_type` | `list[tuple[str, float]]` |
| `fetched_at` | `datetime` |
| `source` | `Literal['live', 'cached']` |

---

### `Candidate` fields

| Field | Type |
|-------|------|
| `slug` | `str` |
| `path` | `str` |
| `current_status` | `str` |
| `evidence` | `list[str]` |
| `snapshot_hash` | `str` |

---

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
| `specs_candidates_enabled` | `bool` | `False` |

### `Config` properties

| Property | Type | Description |
|----------|------|-------------|
| `telemetry_path` | `Path` | Path to the telemetry data file. |
| `runs_dir` | `Path` | Disk root for persisted ops runs. May not exist until first write. |
| `memory_dir` | `Path` | Path to the memory directory. |
| `sessions_dir` | `Path` | Path to the sessions directory. |
| `bulletin_dir` | `Path` | Directory for the multi-actor bulletin's active log and archive. |

---

### `TelemetrySummary` fields

| Field | Type |
|-------|------|
| `total_requests` | `int` |
| `total_cost` | `float` |
| `total_savings` | `float` |
| `by_workflow` | `list[tuple[str, int, float]]` |
| `by_day` | `list[tuple[str, int, float]]` |
| `last_event_at` | `str | None` |

---

### `WorkflowEntry` fields

| Field | Type |
|-------|------|
| `name` | `str` |
| `description` | `str` |
| `stages` | `int` |
| `tier_map` | `dict[str, str]` |

---

### `PathArgSpec` fields

| Field | Type | Default |
|-------|------|---------|
| `kwarg` | `str` | — |
| `required` | `bool` | `False` |

---

### `Feature` fields

| Field | Type | Default |
|-------|------|---------|
| `name` | `str` | — |
| `description` | `str` | — |
| `path` | `str | None` | — |
| `tags` | `tuple[str, ...]` | `()` |

---

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

---

### `FamilyVersion` fields

| Field | Type |
|-------|------|
| `package` | `str` |
| `version` | `str | None` |
| `source` | `str` |

---

### `SpendAlarm` fields

| Field | Type |
|-------|------|
| `level` | `str` — `"ok"` \| `"alarm"` \| `"insufficient_data"` |
| `triggered_by` | `tuple[str, ...]` — subset of `{"daily_anomaly", "ceiling"}` |
| `today_cost` | `float` |
| `baseline_mean` | `float` |
| `baseline_days` | `int` |
| `method` | `str` — `"zscore"` \| `"multiplier"` \| `"none"` |
| `z_score` | `float \| None` |
| `month_to_date` | `float` |
| `monthly_ceiling` | `float` |
| `ceiling_pct` | `float` |
| `source` | `str` — `"account"` \| `"local"` |
| `detail` | `str` — one-line human explanation |

## Functions

The tables below are organized by source module.

### `src/attune/ops/__init__.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | `*args, **kwargs` | — | Lazy-import the FastAPI factory so importing attune doesn't pull FastAPI. |
| `build_config` | `*args, **kwargs` | — | Lazy import of the config builder. |

---

### `src/attune/ops/anthropic_cost.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `clear_cache` | — | `None` | Empty the in-memory cache. Test-only convenience. |
| `load_admin_key` | — | `str | None` | Return the admin API key, or `None` if unavailable. |
| `fetch_summary` | `*, refresh: bool = False` | `tuple[CostSummary | None, CostFetchError | None]` | Return the current cost summary or a categorized error. |

---

### `src/attune/ops/cli.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `add_subparser` | `subparsers: argparse._SubParsersAction` | `None` | Register the `ops` subparser on the main attune CLI parser. |
| `cmd_ops` | `args: argparse.Namespace` | `int` | Run the dashboard server (blocking). Returns `0`. |
| `main` | — | `int` | Standalone entry point: `python -m attune.ops`. |

---

### `src/attune/ops/completion_candidates.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `clear_cache` | — | `None` | Reset the in-memory caches. Test helper. |
| `detect_candidates` | `config: Config, *, now: float | None = None` | `list[Candidate]` | Return all completion candidates across the configured spec roots. |

---

### `src/attune/ops/config.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `attune_home` | — | `Path` | Resolve the user's attune home directory (env override → `~/.attune`). |
| `build_config` | `project_root: Path | None = None, *, host: str = '127.0.0.1', port: int = 8765, allow_run: bool = False, specs_roots: tuple[Path, ...] | None = None, trusted_hosts: tuple[str, ...] | None = None, runs_retention_days: int = 30, specs_candidates_enabled: bool = False` | `Config` | Build a `Config` from inputs and environment defaults. |

---

### `src/attune/ops/data.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_features` | `project_root: Path | str` | `list[Feature]` | Return features parsed from `<project_root>/.help/features.yaml`. |
| `first_feature` | `project_root: Path | str` | `Feature | None` | Return the alphabetically-first feature with a renderable scope. |
| `workflow_default_scope` | `workflow_name: str, project_root: Path | str` | `str` | Return the default scope for one workflow on first paint. |
| `derive_project_name` | `project_root: Path | str` | `str` | Return a human-readable project name for the dashboard header. |
| `claude_sessions_dir` | `project_root: Path | str` | `Path` | Return the canonical directory Claude Code uses to store sessions for this project. |
| `enumerate_project_encoded_keys` | `project_root: Path | str` | `list[Path]` | Return all `~/.claude/projects/` directories belonging to this logical project. |
| `list_recent_sessions_with_paths` | `project_root: Path | str, *, days: int = 3, limit: int | None = DEFAULT_SESSION_LIST_CAP, now: datetime | None = None, parser: Callable[[Path], Session | None] | None = None` | `list[tuple[Session, Path]]` | Same as `list_recent_sessions` but also returns each session's source path. |
| `list_recent_sessions` | `project_root: Path | str, *, days: int = 3, limit: int | None = DEFAULT_SESSION_LIST_CAP, now: datetime | None = None, parser: Callable[[Path], Session | None] | None = None` | `list[Session]` | Return `Session` records for this project's last `days` of activity. |
| `home_kpis` | `summary: TelemetrySummary, *, today: date | None = None` | `HomeKpis` | Derive home-page KPIs from a telemetry summary. |
| `sparkline_points` | `values: list[float], *, width: int = 240, height: int = 40` | `str` | Render values as an SVG `polyline` `points` string. |
| `read_telemetry_summary` | `config: Config, *, recent_days: int = 7, today: date | None = None` | `TelemetrySummary` | Aggregate `usage.jsonl` into a UI-friendly summary. |
| `read_sweep_chip_counts` | `scope_path: str, config: Config` | `SweepChipCounts` | Read the latest persisted sweep result for `scope_path` and tally chips. |
| `read_daily_spend` | `config: Config, *, days: int = 35, today: date \| None = None` | `dict[str, float]` | Daily API spend (USD) bucketed by timestamp from `usage.jsonl`. |
| `spend_alarm` | `daily: dict[str, float], *, today: date \| None = None, monthly_ceiling: float = 350.0, ceiling_fraction: float = 0.8, z_threshold: float = 3.0, flat_multiplier: float = 3.0, min_baseline_days: int = 3, ...` | `SpendAlarm` | Flag anomalous daily API spend and approach to the monthly ceiling. |
| `build_spend_alarm` | `config: Config, cost_summary: Any \| None = None, *, today: date \| None = None` | `SpendAlarm` | Assemble the spend alarm, preferring account-level spend from the cost summary. |
| `list_workflows` | — | `list[WorkflowEntry]` | Return the registered workflow catalog. Empty if the registry is unavailable. |
| `family_versions` | — | `list[FamilyVersion]` | Resolve installed versions for every related attune package. |
| `env_health` | `config: Config` | `dict[str, Any]` | Lightweight environment snapshot for the Health page. |

---

### `src/attune/ops/dismiss_store.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `store_path` | `config: Config` | `Path` | Return the absolute path to the dismiss-store JSON file. |
| `load` | `config: Config` | `dict[str, DismissEntry]` | Read the dismiss store. Missing or corrupt file returns `{}`. |
| `save` | `slug: str, snapshot_hash: str, config: Config, *, ttl_days: int = DEFAULT_TTL_DAYS, now: datetime | None = None` | `None` | Persist a dismiss entry for `slug`, overwriting any prior entry. |
| `clear` | `slug: str, config: Config` | `None` | Remove the entry for `slug`. No-op if absent. |
| `is_active` | `slug: str, current_hash: str, config: Config, *, now: datetime | None = None` | `bool` | Return `True` iff a dismiss for `slug` is currently suppressing it. |

---

### `src/attune/ops/help_data.py`

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `corpus_root` | `config: Config` | `Path` | Return the `.help/templates/` directory for this project. |
| `list_features` | `config: Config` | `list[FeatureSummary]` | All features in the corpus, alphabetical. |
| `get_template` | `config: Config, feature: str, kind: str` | `TemplateRecord | None` | Load one template by feature and kind. Returns `None` if missing. |
| `search` | `config: Config, query: str, *, limit: int = 20` | `list[SearchHit]` | Run a keyword search against the help corpus. |
| `coverage_gaps` | `config: Config` | `GapsReport` | Compute incomplete sets and stale templates across the corpus. |
| `recently_regenerated
