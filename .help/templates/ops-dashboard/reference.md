---
type: reference
name: ops-dashboard-reference
feature: ops-dashboard
depth: reference
generated_at: 2026-05-21T03:19:56.089222+00:00
source_hash: 70c9679ee8d985ef96c30f885e28ddd1a4c9216d86c485efecac67f77809fb67
status: generated
---

# Operations dashboard reference

The operations dashboard provides a web interface for monitoring workflows, costs, sessions, and project specs. Access it via `python -m attune.ops` or the `attune ops` command.

## Core classes

### Configuration

| Class | Description |
|-------|-------------|
| `Config` | Configuration for the dashboard server and project state |
| `TrustedHostMiddleware` | Middleware that rejects requests from untrusted hosts |

#### Config fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `project_root` | `Path` | | Project root directory |
| `attune_home` | `Path` | | Attune state directory |
| `host` | `str` | `'127.0.0.1'` | Server bind address |
| `port` | `int` | `8765` | Server port |
| `allow_run` | `bool` | `False` | Whether to enable workflow execution |
| `specs_roots` | `tuple[Path, ...]` | `()` | Spec directory roots |
| `trusted_hosts` | `tuple[str, ...]` | `()` | Allowed Host headers |
| `runs_retention_days` | `int` | `30` | Days to retain run records |
| `specs_candidates_enabled` | `bool` | `False` | Enable spec completion detection |

#### Config properties

| Property | Type | Description |
|----------|------|-------------|
| `telemetry_path` | `Path` | Path to telemetry data file |
| `runs_dir` | `Path` | Directory for persisted workflow runs |
| `memory_dir` | `Path` | Memory persistence directory |
| `sessions_dir` | `Path` | Claude sessions directory |

### Cost reporting

| Class | Description |
|-------|-------------|
| `CostSummary` | Account-level cost data from Anthropic admin API |
| `CostFetchError` | Categorized cost fetch failure |

#### CostSummary fields

| Field | Type | Description |
|-------|------|-------------|
| `today_usd` | `float` | Today's cost in USD |
| `seven_day_usd` | `float` | Last 7 days cost |
| `month_to_date_usd` | `float` | Month-to-date cost |
| `thirty_day_usd` | `float` | Last 30 days cost |
| `by_day` | `list[tuple[date, float]]` | Daily cost breakdown |
| `by_model` | `list[tuple[str, float]]` | Cost by model |
| `by_cost_type` | `list[tuple[str, float]]` | Cost by type |
| `fetched_at` | `datetime` | Fetch timestamp |
| `source` | `Literal['live', 'cached']` | Data source |

#### CostFetchError fields

| Field | Type | Description |
|-------|------|-------------|
| `kind` | `CostFetchErrorKind` | Error category |
| `message` | `str` | Error message |

### Workflow execution

| Class | Description |
|-------|-------------|
| `Run` | Single workflow execution and its broadcast state |
| `RunnerService` | Workflow execution service with concurrency control |
| `RunnerBusyError` | Exception raised when runner is already busy |

### Sessions

| Class | Description |
|-------|-------------|
| `Session` | Claude Code session for dashboard display |
| `SummaryResult` | Session summary result from AI or cache |
| `CachedSummary` | Persisted session summary with validation metadata |
| `RedactionResult` | Outcome of content redaction |

#### Session fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Session identifier |
| `started_at` | `str` | Start timestamp |
| `last_activity` | `str` | Last activity timestamp |
| `duration_seconds` | `float` | Session duration |
| `message_count` | `int` | Number of messages |
| `starter_prompt` | `str` | Initial prompt |
| `source` | `str` | How session was detected |

### Spec management

| Class | Description |
|-------|-------------|
| `Candidate` | Spec completion candidate |
| `SpecRecord` | Spec summary with phase file status |
| `SpecPhase` | Individual phase file status |

#### Candidate fields

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | Candidate identifier |
| `path` | `str` | File path |
| `current_status` | `str` | Current status |
| `evidence` | `list[str]` | Evidence for completion |
| `snapshot_hash` | `str` | Content hash |

### Data structures

| Class | Description |
|-------|-------------|
| `TelemetrySummary` | Aggregated usage telemetry |
| `WorkflowEntry` | Workflow catalog entry |
| `PathArgSpec` | CLI path argument specification |
| `Feature` | Feature from `.help/features.yaml` |
| `FamilyVersion` | Package version information |

## Functions

### Application lifecycle

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | `*args, **kwargs` | | Lazy FastAPI application factory |
| `build_config` | `*args, **kwargs` | | Configuration builder |
| `main` | | `int` | Standalone entry point |
| `cmd_ops` | `args: argparse.Namespace` | `int` | CLI command handler |

### Cost reporting

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_admin_key` | | `str \| None` | Load Anthropic admin API key |
| `fetch_summary` | `*, refresh: bool = False` | `tuple[CostSummary \| None, CostFetchError \| None]` | Fetch current cost summary |
| `clear_cache` | | `None` | Clear cost cache |

### Spec detection

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `detect_candidates` | `config: Config, *, now: float \| None = None` | `list[Candidate]` | Find spec completion candidates |
| `clear_cache` | | `None` | Reset candidate cache |

### Data access

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `list_features` | | | Parse features from `.help/features.yaml` |
| `list_recent_sessions` | | | Recent Claude Code sessions |
| `read_telemetry_summary` | | | Aggregate usage telemetry |
| `list_workflows` | | | Available workflow catalog |
| `family_versions` | | | Installed package versions |

## Constants

### API configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `_COST_REPORT_URL` | `'https://api.anthropic.com/v1/organizations/cost_report'` | Anthropic cost API endpoint |
| `_API_VERSION` | `'2023-06-01'` | API version header |

### File patterns

| Constant | Value | Description |
|----------|-------|-------------|
| `_PR_REF_FILES` | `('decisions.md', 'tasks.md')` | Pull request reference files |
| `_PHASE_FILES` | `('decisions.md', 'requirements.md', 'design.md', 'tasks.md')` | Spec phase files |
| `STORE_FILENAME` | `'spec_completion_dismissed.json'` | Dismissal store file |
| `SETTINGS_FILENAME` | `'config.json'` | Settings file |

### Status values

| Constant | Value | Description |
|----------|-------|-------------|
| `_VALID_STATUSES` | `('draft', 'in-review', 'approved', 'complete', 'completed', 'done')` | Valid spec statuses |
| `_COMPLETE_LIKE_STATUSES` | `{'complete', 'completed', 'done'}` | Completion status variants |
| `_VALID_BUCKETS` | `('queue', 'questions', 'rejected')` | Valid spec buckets |

### UI events

| Constant | Value | Description |
|----------|-------|-------------|
| `EVENTS` | `('pill_click', 'rec_card_click', 'scope_picker_change')` | Tracked UI interactions |
