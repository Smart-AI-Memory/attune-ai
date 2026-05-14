---
type: tutorial
name: ops-dashboard
tags: [ops, dashboard, runner, workflows, scope-picker, persistence, sse]
source: developer-guidance
---

# Tutorial: Ops Dashboard

You are going to build a running local ops dashboard — a FastAPI-backed server that exposes a workflow runner with a per-feature scope picker, persisted run history, and live SSE log streaming. When you finish, you will have a process you can open in a browser and use to trigger attune workflows against a real project directory.

## Prerequisites

- Python 3.10 or newer
- `attune` installed in your environment (`pip install attune`)
- A project directory on disk (any folder with at least one workflow configured)

## What you will build

A local server started from Python that:

1. Reads your project and attune state through a `Config` object
2. Serves the ops dashboard on `http://127.0.0.1:8765`
3. Exposes KPI numbers and a cost sparkline on the home page
4. Lists features and workflows scoped to your project directory

You will write roughly fifteen lines of Python and end up with a browser tab showing live dashboard data.

---

## Step 1 — Import the public API

The `attune.ops` module uses lazy imports so that loading `attune` in other contexts doesn't pull FastAPI into memory. Import only what the public API exposes:

```python
from attune.ops import create_app, build_config
```

**You should see:** no import errors. If you get `ModuleNotFoundError`, confirm that `attune` is installed in the active virtual environment.

---

## Step 2 — Build a `Config` for your project

`Config` is the single source of truth for where the dashboard reads project state and attune data. You build one with `build_config`, which resolves environment defaults for anything you leave unspecified:

```python
from pathlib import Path

config = build_config(
    project_root=Path("."),   # your project directory
    host="127.0.0.1",
    port=8765,
)
```

`build_config` fills in `attune_home` automatically (checking the `ATTUNE_HOME` environment variable, then falling back to `~/.attune`), so you only need to supply values that differ from the defaults.

**You should see:** a `Config` instance. Print it to confirm the paths resolved correctly:

```python
print(config.project_root)   # absolute path to your project
print(config.attune_home)    # e.g. /home/you/.attune
print(config.runs_dir)       # where run history will be persisted
```

---

## Step 3 — Inspect what the dashboard will surface

Before starting the server, confirm that the dashboard can find your project's features. This step teaches you the data model the home page is built from.

`list_features` reads `.help/features.yaml` from your project root and returns a list of `Feature` objects — one per entry in that file:

```python
from attune.ops import build_config
from attune.ops._readers import list_features, first_feature

features = list_features(config.project_root)
for f in features:
    print(f.name, f.path, f.tags)

lead = first_feature(config.project_root)
print("Scope picker will default to:", lead)
```

Each `Feature` has a `name`, a `description`, an optional `path` (used as the scope argument), and a tuple of `tags`. The scope picker in the dashboard UI uses exactly this list.

**You should see:** one line per feature defined in `.help/features.yaml`. If the file doesn't exist yet, both calls return an empty list / `None` — that's fine; the dashboard still starts.

---

## Step 4 — Create the FastAPI application

`create_app` wraps the FastAPI factory. Calling it wires up all routes — the home page KPIs, the workflow runner endpoints, the SSE log stream, and the `TrustedHostMiddleware` that guards the server using `config.trusted_hosts`:

```python
app = create_app(config)
```

`create_app` is intentionally lazy: it imports FastAPI only at this call site, not at module import time. That is why it takes a `Config` rather than raw kwargs — all runtime decisions are already resolved before the factory runs.

**You should see:** a FastAPI application object. Confirm with:

```python
print(type(app))   # <class 'fastapi.applications.FastAPI'>
print([r.path for r in app.routes])  # list of registered URL paths
```

---

## Step 5 — Start the server

Use `uvicorn` to serve the app. The dashboard is a blocking process, so run this as the last statement in your script (or from the command line):

```python
import uvicorn

uvicorn.run(app, host=config.host, port=config.port)
```

Alternatively, use the built-in CLI entrypoint, which does exactly the same thing:

```bash
attune ops
```

Or invoke the module directly:

```bash
python -m attune.ops
```

**You should see:** uvicorn startup lines followed by:

```
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
```

Open `http://127.0.0.1:8765` in a browser. The home page should display today's event count, today's cost, and a seven-day cost sparkline drawn from your telemetry data in `~/.attune`.

---

## Step 6 — Verify the KPI data model

While the server is running, step back and look at how the home page numbers are derived. `home_kpis` takes a `TelemetrySummary` and produces a `HomeKpis` — this is what the dashboard's home-page endpoint calls internally:

```python
from datetime import date
from attune.ops._readers import home_kpis
from attune.ops._models import TelemetrySummary

# Construct a minimal summary to see the shape of the output
summary = TelemetrySummary(
    total_requests=42,
    total_cost=1.25,
    total_savings=0.30,
    by_workflow=[("my-workflow", 10, 0.50)],
    by_day=[("2026-05-14", 10, 0.50)],
    last_event_at="2026-05-14T12:00:00",
)

kpis = home_kpis(summary, today=date(2026, 5, 14))
print(kpis.today_events)       # 10
print(kpis.seven_day_cost)     # 0.50
print(kpis.sparkline)          # list[DailyCost]
```

`HomeKpis.sparkline` is the list of `DailyCost` objects that the front end uses to draw the cost chart. Each `DailyCost` holds a `day` string, an `events` count, and a `cost` float.

**You should see:** the printed values match what you put into `TelemetrySummary`. This confirms you understand the data flow from raw telemetry to the numbers above the fold.

---

## What you learned

- **Step 2** — `build_config` is the single place where project paths, host/port, and attune home are resolved. You never pass raw strings to `create_app`.
- **Step 3** — The scope picker is backed by `list_features`, which reads `.help/features.yaml`. If that file is empty or absent, the picker is empty — not broken.
- **Step 4** — `create_app` is a lazy factory. FastAPI is imported only when you call it, keeping `attune` importable in environments that don't have FastAPI installed.
- **Step 5** — The same server is reachable three ways: as a library (`uvicorn.run(app, ...)`), as a CLI subcommand (`attune ops`), or as a module (`python -m attune.ops`). All three paths converge on the same `Config` and `create_app`.
- **Step 6** — `home_kpis` is a pure function. You can unit-test the KPI logic without starting a server by constructing a `TelemetrySummary` directly.

## Next steps

Read the `attune.ops` reference to see every `Config` field, the full `TelemetrySummary` schema, and the complete list of URL routes the dashboard registers — that's the right place to look when you need to customise retention, add trusted hosts, or integrate the dashboard into a larger application.

<!-- attune-generated: source_hash=395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42 feature=ops-dashboard kind=tutorial generated_at=2026-05-14 -->
