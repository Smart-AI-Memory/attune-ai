---
type: task
name: ops-dashboard-task
feature: ops-dashboard
depth: task
generated_at: 2026-06-24T12:00:17.825226+00:00
source_hash: 1cad6797952953474159da11cd78e2e6f3b36b4845377e700eb2570427d138e7
status: generated
---

# The local FastAPI operations dashboard — a workflow runner with per-feature scope, persisted run history, workflow chaining, and live SSE log streaming

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
