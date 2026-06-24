---
type: faq
name: ops-dashboard-faq
feature: ops-dashboard
depth: faq
status: manual
---

# Ops Dashboard FAQ

## What is the ops dashboard?

A local FastAPI web app that lets you run attune workflows against a
specific feature scope, browse persisted run history, chain workflows
with a single click, and stream live logs over SSE. Start it with
`attune ops` or `python -m attune.ops` (default `127.0.0.1:8765`).

## How do I start it?

Run `attune ops` (the CLI subcommand registered by `add_subparser()`) or
`python -m attune.ops` (calls `main()`). Both block until you stop the
server. Workflow execution is **enabled by default**; pass `--read-only`
for a look-but-don't-run dashboard.

## What's the public API?

Exactly three names — `attune.ops.__all__` is `create_app`,
`build_config`, and `Config`. Build a config with `build_config(...)`
(don't instantiate `Config` directly), then `create_app(config)` returns
the `FastAPI` app. Both are synchronous. The runner lives in
`attune.ops.runner`.

## What does `Config` control?

`Config` anchors every path the dashboard reads or writes. Key fields:
`host`/`port` (default `127.0.0.1:8765`), `allow_run` (default `False`),
`specs_roots`, `runs_retention_days` (default 30), and
`specs_candidates_enabled`. Derived **properties** (no parentheses)
include `runs_dir`, `sessions_dir`, `bulletin_dir`, `memory_dir`, and
`telemetry_path`.

## Why won't my workflow run?

`Config.allow_run` must be `True`. It defaults to `False`; the CLI
enables it (`allow_run = not --read-only`), so `attune ops` can run
workflows out of the box while `attune ops --read-only` cannot.

## How do I run a workflow from Python?

Use `RunnerService`. Its `start(workflow, *, path=None)` method is a
**coroutine** — `await` it; it returns a `Run`. Only one run is active
at a time, so a concurrent `start()` raises `RunnerBusyError` (which
carries `current_run_id`).

## How does the live log stream work?

`Run.subscribe()` is an **async iterator** of events — the SSE feed the
browser consumes. Iterate it with `async for`; `Run.is_terminal` (a
property) flips true when the run finishes.

## Does the dashboard own the cost / telemetry / help data it shows?

No. Those are **adjacent** read-only surfaces it renders:
`ops.anthropic_cost.fetch_summary()` (account cost), `ops.data` (reads
the telemetry store), and `ops.help_data` (the help tab). Each is owned
by its own feature (telemetry, help-system); the dashboard only displays
them.

## How do I label a spec's lifecycle?

`ops.spec_lifecycle.derive_lifecycle(spec, *, now=None)` returns a status
string from the spec's phases and last-modified time. That is the only
public function in the module — there is no candidate-detection API.

## How long is run history kept?

`runs_retention_days` (default 30). History is persisted to
`Config.runs_dir` and survives restarts (`get_or_load` rehydrates a past
run); `prune_old_runs` trims older entries.

## Where are the source files?

- `src/attune/ops/**`
