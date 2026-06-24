---
type: reference
name: ops-dashboard-reference
feature: ops-dashboard
depth: reference
generated_at: 2026-06-24T12:00:17.825226+00:00
source_hash: 1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7
status: generated
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

## Reference

The public API is `create_app`, `build_config`, and `Config`, exported
from `attune.ops`. The runner and read-side helpers are imported from
their submodules.

### `attune.ops`

| Symbol | Purpose |
|---|---|
| `build_config(project_root=None, *, host="127.0.0.1", port=8765, allow_run=False, specs_roots=None, trusted_hosts=None, runs_retention_days=30, specs_candidates_enabled=False) -> Config` | Build the dashboard config. |
| `create_app(config, *, runner=None) -> FastAPI` | Build the FastAPI app (sync). |
| `Config` | Settings dataclass. **Properties:** `bulletin_dir`, `memory_dir`, `runs_dir`, `sessions_dir`, `telemetry_path`. `allow_run` defaults `False`. |

### `attune.ops.runner`

| Symbol | Purpose |
|---|---|
| `RunnerService(*, history_limit=20, command_builder=None, executor=None, persistence_dir=None, project_root=None, bulletin=None, actor_id=None, actor_kind="dashboard")` | Workflow runner. |
| `RunnerService.start(workflow, *, path=None) -> Run` | **Async.** Launch a run (one at a time). |
| `RunnerService.recent` / `.get` / `.get_or_load` / `.handle_stdout_line` | Sync history/lookup helpers. |
| `RunnerService.current` / `.persistence_dir` | Properties. |
| `Run.subscribe() -> AsyncIterator` | **Async.** SSE event feed. |
| `Run.append_line` / `.mark_done` / `.to_dict` / `.to_record` | Sync run helpers. |
| `Run.duration_seconds` / `.is_terminal` | Properties. |
| `RunnerBusyError(current_run_id)` | Raised on a concurrent `start()`. |
| `prune_old_runs(...)` / `echo_command_builder` | Retention + a default command builder. |

### Read-side submodules

| Module | Key public API |
|---|---|
| `ops.data` | `read_telemetry_summary`, `list_workflows`, `list_features`, `home_kpis`, `list_recent_sessions`, `env_health`, `family_versions`, `workflow_default_scope`, `sparkline_points`, … |
| `ops.anthropic_cost` | `fetch_summary(*, refresh=False) -> tuple[CostSummary \| None, CostFetchError \| None]`; `CostSummary`, `CostFetchError`, `CostFetchErrorKind`. |
| `ops.help_data` | `coverage_gaps`, `search`, `list_features`, `get_template`. |
| `ops.spec_lifecycle` | `derive_lifecycle(spec, *, now=None) -> str` (only public function) + `STALE_THRESHOLD_DAYS`. |
| `ops.interaction_counters` | `EVENTS = ('pill_click', 'rec_card_click', 'scope_picker_change')`. |
| `ops.cli` | `add_subparser`, `cmd_ops`, `main`. |

### CLI flags (`attune ops` / `python -m attune.ops`)

| Flag | Effect |
|---|---|
| `--host` / `--port` | Bind address (default `127.0.0.1:8765`). |
| `--project-root` | Project to serve. |
| `--no-browser` | Don't auto-open a browser. |
| `--read-only` | Disable runs (`allow_run=False`); runs are **enabled** otherwise. |
| `--specs-root DIR` | Spec directory (repeatable). |
| `--trusted-host` | Allow a remote host. |
| `--runs-retention-days` | History retention (default 30). |
| `--specs-candidates` / `--no-specs-candidates` | Toggle spec candidate display. |
