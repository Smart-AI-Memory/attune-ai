# Ops Dashboard

## Quickstart

Start the dashboard from the CLI (runs enabled unless `--read-only`):

```bash
attune ops                 # http://127.0.0.1:8765
python -m attune.ops --read-only --port 9000
```

Build the app from Python (e.g. to embed or test it):

```python
from pathlib import Path

from attune.ops import build_config, create_app

config = build_config(Path("."), host="127.0.0.1", port=8765)
app = create_app(config)
print(type(app).__name__, "| runs allowed:", config.allow_run)
```

## Tasks

### Configure where the dashboard reads and writes

**Goal:** point the dashboard at a project and inspect its derived
paths.

**Steps:**

```python
from pathlib import Path

from attune.ops import build_config

config = build_config(Path("."), runs_retention_days=14)
print("runs:", config.runs_dir)
print("sessions:", config.sessions_dir)
print("telemetry:", config.telemetry_path)
```

**Verify:** `build_config()` returns a `Config`. `runs_dir`,
`sessions_dir`, and `telemetry_path` are **properties** (no `()`), all
anchored under the attune home / project root.

### Run a workflow with the runner

**Goal:** execute a workflow and get a `Run` back.

**Steps:**

```python
import asyncio

from attune.ops.runner import RunnerService, RunnerBusyError


async def main() -> None:
    runner = RunnerService()
    try:
        run = await runner.start("security-audit", path="src/attune/config")
        print("started:", run.id)
    except RunnerBusyError as exc:
        print("busy with:", exc.current_run_id)


asyncio.run(main())
```

**Verify:** `start()` is a **coroutine** — `await` it; it returns a
`Run`. Only one run is active at a time, so a concurrent `start()`
raises `RunnerBusyError`.

### Stream a run's output over SSE

**Goal:** consume a run's live event feed (what the browser does).

**Steps:**

```python
async def stream(run) -> None:
    async for event in run.subscribe():
        print(event)
        if run.is_terminal:
            break
```

**Verify:** `Run.subscribe()` is an **async iterator** of events;
`is_terminal` flips true when the run finishes.

### Label a spec's lifecycle

**Goal:** ask the dashboard's spec helper what bucket a spec is in.

**Steps:**

```python
from types import SimpleNamespace

from attune.ops.spec_lifecycle import derive_lifecycle

spec = SimpleNamespace(phases=[], last_modified=None)
print(derive_lifecycle(spec))
```

**Verify:** `derive_lifecycle(spec, *, now=None)` returns a status
**string**. It is the only public function in `ops.spec_lifecycle`.

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

<!-- attune-generated: source_hash=1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7 feature=ops-dashboard kind=how-to generated_at=2026-06-24 -->
