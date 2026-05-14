# Ops Dashboard architecture

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

## Purpose

`attune ops` serves as the workflow OS's local web dashboard. It is responsible for: presenting home-page KPIs and cost sparklines, letting users pick a feature scope and trigger workflow runs, streaming live run output over SSE, persisting run history to disk, and enforcing trusted-host access control.

It is **not** responsible for defining workflows themselves, managing the attune agent, or writing telemetry data — those concerns live outside this module. `attune ops` reads telemetry and run state; it does not produce them.

## Key classes

| Class | Responsibility | File |
|-------|----------------|------|
| `Config` | Holds all resolved paths and server settings (host, port, retention policy, trusted hosts) that the dashboard reads at startup. | `src/attune/ops/config.py` |
| `TrustedHostMiddleware` | Rejects any request whose `Host` header is not on the configured allowlist before it reaches a route handler. | `src/attune/ops/middleware.py` |
| `RunnerService` | Owns the run history list and the concurrency lock; enforces the one-active-run-at-a-time constraint. | `src/attune/ops/runner.py` |
| `Run` | Represents a single workflow execution and its associated SSE broadcast state; created and managed by `RunnerService`. | `src/attune/ops/runner.py` |
| `RunnerBusyError` | Signals that a new run was requested while one is already pending or running; raised by `RunnerService`. | `src/attune/ops/runner.py` |
| `HomeKpis` | Aggregates today's event count, rolling 7-day cost and savings, and the sparkline data shown above the fold on the home page. | `src/attune/ops/data.py` |
| `DailyCost` | Carries one day's event count and cost; the list of these forms the sparkline fed into `HomeKpis`. | `src/attune/ops/data.py` |
| `TelemetrySummary` | Read-only snapshot of aggregate telemetry: total requests, cost, savings, and breakdowns by workflow and by day. | `src/attune/ops/data.py` |
| `WorkflowEntry` | Describes one workflow available for dispatch: name, description, stage count, and CLI tier mapping. | `src/attune/ops/data.py` |
| `PathArgSpec` | Describes how a workflow accepts a scope path on the CLI (`kwarg` name and whether it is required). | `src/attune/ops/data.py` |
| `Feature` | Represents one entry from `.help/features.yaml`; drives the scope picker that lets users target a specific feature path. | `src/attune/ops/data.py` |
| `FamilyVersion` | Records one package's resolved version and source; used by the dashboard to surface dependency info. | `src/attune/ops/data.py` |
| `SpecPhase` | Snapshot of one phase file's existence and status string within a spec directory. | `src/attune/ops/routes/specs.py` |
| `SpecRecord` | Aggregates a spec directory's path and the `SpecPhase` snapshot for each of the four phase files (`decisions.md`, `requirements.md`, `design.md`, `tasks.md`). | `src/attune/ops/routes/specs.py` |

> **Note:** `Run` and `RunnerService` together do three things — execution lifecycle, SSE broadcast state, and history retention — which may be worth splitting if the runner grows more complex.

## Data flow

```
CLI / browser request
        |
        v
TrustedHostMiddleware  ──── rejects unlisted Host headers
        |
        v
   FastAPI app  (create_app())
   ┌────────────────────────────────────────────┐
   │                                            │
   │  GET /                                     │
   │    TelemetrySummary ──> home_kpis()        │
   │                             └──> HomeKpis  │
   │                                   (KPI     │
   │                                    panel + │
   │                                    sparkline│
   │                                    of      │
   │                                    DailyCost)
   │                                            │
   │  GET /workflows                            │
   │    WorkflowEntry[]  (scope: PathArgSpec)   │
   │                                            │
   │  GET /features                             │
   │    list_features() ──> Feature[]           │
   │    first_feature() ──> Feature | None      │
   │                                            │
   │  POST /run                                 │
   │    RunnerService.start()                   │
   │      ├── RunnerBusyError (409 if busy)     │
   │      └── Run (new execution)               │
   │            └── SSE stream  (/run/{id}/log) │
   │                                            │
   │  GET /specs                                │
   │    SpecRecord[]                            │
   │      └── SpecPhase × 4 per spec           │
   └────────────────────────────────────────────┘
        |
        v
  Config  (read at startup: paths, host, port,
           trusted_hosts, runs_retention_days)
  ├── telemetry_path  →  TelemetrySummary source
  ├── runs_dir        →  persisted Run history
  ├── memory_dir      →  agent memory (read-only)
  └── sessions_dir    →  session records (read-only)
```

## Design decisions

**Lazy FastAPI import via `create_app()`**
`create_app()` and `build_config()` are thin wrappers that import FastAPI only when the dashboard is actually started. This keeps `import attune` fast for all other subcommands that don't need a web server.

**One active run at a time**
`RunnerService` holds a concurrency lock and raises `RunnerBusyError` when a second run is attempted. The alternative — queuing runs — was not chosen because the dashboard is a local single-user tool; silent queueing would obscure whether a previous run was still in progress.

**`Config` as a resolved-paths dataclass, not a live reader**
`build_config()` resolves all paths and environment variables once at startup and freezes them into a `Config` dataclass. Routes read `Config` fields directly rather than re-reading the environment on each request, so there is no ambiguity about which config values are active.

**`allow_run` flag**
Workflow execution is disabled by default (`allow_run = False`). This is an explicit opt-in so that dashboard deployments used purely for observability cannot accidentally trigger runs.

**Trusted-host enforcement at middleware layer**
`TrustedHostMiddleware` runs before any route handler, so the allowlist check cannot be bypassed by a misconfigured route. The `trusted_hosts` tuple in `Config` is the single source of truth for this list.

## Extension points

- **Add a new route:** register it on the FastAPI app returned by `create_app()`. Place data-shape dataclasses in `src/attune/ops/data.py` and route logic under `src/attune/ops/routes/`.
- **Change server settings** (host, port, retention, trusted hosts): pass arguments to `build_config()` or set the corresponding environment variables — `build_config()` merges both sources.
- **Support additional spec phase files:** add filenames to the `_PHASE_FILES` tuple in `src/attune/ops/routes/specs.py`. Valid status strings are governed by `_VALID_STATUSES` in the same file.
- **Extend the scope picker:** add entries to `.help/features.yaml` in the project root. `list_features()` and `first_feature()` parse this file; no code changes are needed for new features.
- **Add a new run backend:** replace or subclass `RunnerService`. The concurrency contract is: raise `RunnerBusyError` if a run is already active, return a `Run` instance otherwise. SSE consumers depend on `Run`'s broadcast interface.

For usage and configuration details, see the `attune ops` reference documentation.
