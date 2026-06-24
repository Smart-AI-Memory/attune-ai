---
feature: ops-dashboard
summary: The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming
tags: [ops, dashboard, runner, workflows, scope-picker, persistence, sse]
source_globs:
  - src/attune/ops/**
nav:
  help: ops-dashboard
  mkdocs:
    how-to: how-to/ops-dashboard
    architecture: architecture/ops-dashboard
    reference: reference/ops-dashboard
---

## Overview

The ops dashboard is attune's **local operations layer** — a FastAPI
web app you run on your own machine to execute workflows against a
chosen feature scope, browse persisted run history, chain workflows
with a click, and watch live logs stream over **SSE**. It lives in
**`src/attune/ops/`** and is launched with `attune ops` (or `python -m
attune.ops`), binding to **`127.0.0.1:8765`** by default.

This page documents the **runner core** — the server, its config, and
the `RunnerService`/`Run` execution model. The dashboard also *displays*
data owned by other features — Anthropic cost (`ops.anthropic_cost`),
telemetry (`ops.data` reads the telemetry store), and help coverage
(`ops.help_data`) — but those are **adjacent** surfaces it renders, not
its own; each belongs to its respective feature (telemetry, help-system).

The public API is deliberately tiny — `__all__` is exactly
**`create_app`, `build_config`, `Config`**. Everything else
(`RunnerService`, `Run`, the `ops.data` readers) is reached through
those or imported from its submodule.

You reach it these ways:

- the **CLI** — `attune ops` / `python -m attune.ops` starts the server;
- the **Python API** — `from attune.ops import create_app, build_config,
  Config` to build and embed the app (e.g. in tests).

## Concepts

### The public surface: `build_config` → `create_app`

`build_config(project_root, *, host, port, allow_run, …)` produces a
`Config`; `create_app(config, *, runner=None)` returns a ready
`FastAPI` app. Both are **synchronous**. `Config` anchors every path the
dashboard reads or writes via derived **properties**: `runs_dir`,
`sessions_dir`, `bulletin_dir`, `memory_dir`, `telemetry_path`
(`attune_home()` resolves the attune state root).

### The run-safety gate

`Config.allow_run` defaults to **`False`** — the dashboard will not
execute a workflow unless it is `True`. The **CLI flips it on by
default**, disabling it only when you pass `--read-only`. So `attune
ops` can run workflows out of the box; `attune ops --read-only` serves a
look-but-don't-run dashboard.

### `RunnerService` and `Run` — the execution model

`RunnerService` owns workflow execution. Its one **async** method is the
killer to remember:

- **`start(workflow, *, path=None) -> Run` is a coroutine** — `await`
  it. It launches a workflow (optionally scoped to a `path`) and returns
  a `Run`.
- `recent`, `get`, `get_or_load`, `handle_stdout_line` are
  **synchronous**; `current` and `persistence_dir` are properties.
- Only **one run at a time**: starting a second while one is active
  raises **`RunnerBusyError(current_run_id)`**.

A `Run` is one execution. `Run.subscribe()` is an **async iterator** of
events — this is the SSE feed the browser consumes. `append_line`,
`mark_done`, `to_dict`/`to_record` are sync; `duration_seconds` and
`is_terminal` are properties.

### Scope picker, persistence, and chaining

The feature **scope picker** reads `.help/features.yaml` so you can
narrow a run to one feature; `ops.data.workflow_default_scope` supplies
the default. Run history is **persisted** to `Config.runs_dir` and
survives restarts (`get_or_load` rehydrates a past run);
`prune_old_runs` trims beyond `runs_retention_days` (default 30). UI
interactions are counted via `ops.interaction_counters.EVENTS`
(`pill_click`, `rec_card_click`, `scope_picker_change`).

### Adjacent read-only surfaces

The dashboard renders data it does not own:

| Submodule | Role | Owning feature |
|---|---|---|
| `ops.data` | Reads telemetry/workflows/sessions/KPIs | telemetry |
| `ops.anthropic_cost` | `fetch_summary()` → cost report | (account-level) |
| `ops.help_data` | Help coverage + search (the help tab) | help-system |
| `ops.spec_lifecycle` | `derive_lifecycle(spec)` → status label | spec tooling |

`ops.spec_lifecycle`'s only public function is `derive_lifecycle(spec,
*, now=None) -> str` (plus the `STALE_THRESHOLD_DAYS` constant) — it
labels a spec's lifecycle bucket from its phases and last-modified time.
(There is no candidate-detection API here.)

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

## Comparison

The ops dashboard is one of three front doors to attune's workflows:

| | ops-dashboard | mcp-server | CLI |
|--|---------------|-----------|-----|
| Surface | Local web UI (HTTP) | MCP tools (stdio) | `attune workflow run` |
| Strength | Scope picker, run history, chaining, live SSE | In-conversation tool calls | Scriptable one-shots |
| Entry | `attune ops` | `python -m attune.mcp.server` | `attune workflow run <slug>` |

It is the *browser* front door; the MCP server is the *conversational*
one; the CLI is the *terminal* one. The dashboard renders cost,
telemetry, and help data those other features own.

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `RuntimeWarning: coroutine 'RunnerService.start' was never awaited` | `start()` called without `await` | It's async — `await` it / `asyncio.run` | high |
| Workflows won't run from the UI | `Config.allow_run` is `False` (e.g. `--read-only`) | Start without `--read-only` | high |
| `RunnerBusyError` on start | A run is already active (one at a time) | Wait for / inspect `runner.current` | medium |
| `TypeError` calling `config.runs_dir()` | `runs_dir` is a property | Drop the `()` | medium |
| Cost panel shows an error | `fetch_summary` returned a `CostFetchError` (no admin key, network) | Inspect the error `kind`/`message`; cost is an adjacent surface | low |

### Risk areas

- **`RunnerService.start` and `Run.subscribe` are async.** They are the
  two awaitable surfaces; everything else on the runner is sync.
- **`allow_run` is a real gate.** Off by default in `Config`; the CLI
  turns it on unless `--read-only`.
- **Scope confusion.** Cost/telemetry/help shown on the dashboard are
  *adjacent* surfaces — owned by other features, only read here.

### Diagnosis order

1. Confirm the app builds: `create_app(build_config(Path(".")))`.
2. Confirm runs are allowed: `config.allow_run` (and no `--read-only`).
3. For a run that won't start: check `runner.current` /
   `RunnerBusyError`.
4. For async warnings: `await` `start()` / iterate `subscribe()`.
5. For a data panel: that data is owned by its feature (telemetry /
   help-system / cost).

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** What is the ops dashboard?
  **A:** A local FastAPI web app for running attune workflows against a
  feature scope, with persisted run history, workflow chaining, and live
  SSE log streaming. Start it with `attune ops` (default
  `127.0.0.1:8765`).
- **Q:** How do I start it?
  **A:** `attune ops` or `python -m attune.ops`. Runs are enabled by
  default; pass `--read-only` for a look-but-don't-run dashboard.
- **Q:** What's the public API?
  **A:** Exactly `create_app`, `build_config`, and `Config`
  (`attune.ops.__all__`). The runner is `attune.ops.runner`.
- **Q:** Why won't my workflow run?
  **A:** `Config.allow_run` must be `True`. It defaults to `False`; the
  CLI enables it unless you pass `--read-only`.
- **Q:** What's async on the runner?
  **A:** `RunnerService.start()` and `Run.subscribe()`. The history and
  lookup helpers (`recent`, `get`, `get_or_load`) are synchronous.
- **Q:** Can I run two workflows at once?
  **A:** No — one at a time. A concurrent `start()` raises
  `RunnerBusyError`.
- **Q:** Does it own the cost/telemetry/help data it shows?
  **A:** No. Those are adjacent surfaces — `ops.data`/
  `ops.anthropic_cost`/`ops.help_data` only read data owned by the
  telemetry and help-system features.

## Notes & tips

- **Depend on the documented public surface:** `create_app`,
  `build_config`, `Config` from `attune.ops`. The runner and readers are
  reached from their submodules.
- **`await` the two async surfaces.** `RunnerService.start` and
  `Run.subscribe`; everything else on the runner is sync.
- **Paths are properties.** `runs_dir`, `sessions_dir`,
  `telemetry_path` — no `()`.
- **`--read-only` for a safe demo.** It serves the dashboard with
  execution disabled.

## Design & extension

### Design decisions

- **Tiny public surface.** `__all__` is just `create_app`,
  `build_config`, `Config` — the runner and readers stay internal-ish so
  the supported API is small and stable.
- **Runs off by default in `Config`.** Execution is opt-in
  (`allow_run`); the CLI enables it deliberately so embedding the app is
  safe by default.
- **One run at a time.** `RunnerService` is single-flight
  (`RunnerBusyError`), keeping run state and the SSE feed unambiguous.
- **Read-only adjacency.** The dashboard *renders* cost/telemetry/help
  via `ops.data`/`ops.anthropic_cost`/`ops.help_data` but never owns
  that data — each stays the responsibility of its feature.

### Extension points

- **Custom command builder / executor:** pass `command_builder` /
  `executor` to `RunnerService` (default `echo_command_builder`).
- **Inject a runner:** `create_app(config, runner=...)` for tests or a
  custom execution backend.
- **Retention:** tune `runs_retention_days` (or call `prune_old_runs`).
- **New read panel:** add a reader to `ops.data` and surface it in the
  app — keep ownership with the source feature.
