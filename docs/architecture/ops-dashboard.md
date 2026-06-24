# Ops Dashboard

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

<!-- attune-generated: source_hash=1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7 feature=ops-dashboard kind=architecture generated_at=2026-06-24 -->
