---
type: warning
name: ops-dashboard-warning
feature: ops-dashboard
depth: warning
generated_at: 2026-06-24T12:00:17.825226+00:00
source_hash: 1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7
status: generated
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

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
