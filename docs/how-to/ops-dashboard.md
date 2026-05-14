---
type: how-to
name: ops-dashboard
tags: [ops, dashboard, runner, workflows, scope-picker, persistence, sse]
source: ops-dashboard
---

# How to use the ops dashboard

Use this guide when you want to launch the attune operations dashboard, configure its server settings, and work with its core APIs to surface workflow runs, telemetry, and spec status in your project.

## Quick start

Start the dashboard from the command line against your project root:

```bash
attune ops --project-root /path/to/your/project --port 8765
```

Or launch it directly as a Python module:

```bash
python -m attune.ops
```

The dashboard starts a blocking server at `http://127.0.0.1:8765`. Open that URL to see the home page with today's KPIs, a cost sparkline, and the workflow catalog. Press `Ctrl+C` in the terminal to stop the server.

## Core API

| Function or class | Purpose |
|---|---|
| `build_config(project_root, *, host, port, allow_run, ...)` | Build a `Config` from explicit inputs and environment defaults. |
| `create_app()` | Build the FastAPI app, wiring `Config` and templates into request state. |
| `cmd_ops(args)` | Run the dashboard server (blocking); returns `0` on clean exit. |
| `main()` | Standalone entry point for `python -m attune.ops`. |
| `attune_home()` | Resolve the user's attune home directory (`ATTUNE_HOME` env override → `~/.attune`). |
| `list_features(project_root)` | Return features parsed from `<project_root>/.help/features.yaml`. |
| `first_feature(project_root)` | Return the alphabetically first feature that has a renderable scope. |
| `home_kpis(summary, *, today)` | Derive home-page KPI numbers from a `TelemetrySummary`. |
| `list_workflows()` | Return the registered workflow catalog; empty list if the registry is unavailable. |
| `env_health()` | Lightweight environment snapshot for the Health page. |
| `family_versions()` | Resolve installed versions for every related attune package. |
| `list_runs(workflow)` | Return up to 20 newest runs for a workflow, newest first. |
| `prune_old_runs(days)` | Delete persisted run files older than `days`; returns the deletion count. |
| `list_specs()` | Federated listing of specs across all configured spec roots. |
| `update_phase_status()` | Rewrite the `**Status**` line in a named phase file. |
| `read_telemetry_summary()` | Aggregate `usage.jsonl` into a UI-friendly `TelemetrySummary`. |
| `compute_allowlist()` | Compute the merged default + user-supplied `Host` header allowlist. |
| `is_persistence_enabled()` | Returns `True` when `ATTUNE_OPS_SWEEP_RESULTS` is set to a non-empty value. |
| `persist_result()` | Atomically write a `SweepResult` to `<attune_home>/ops/sweep-results/<hash>.json`. |
| `watch_and_persist()` | Subscribe to a discovery-sweep run and persist its result on success. |

### Key dataclasses

| Class | Purpose |
|---|---|
| `Config` | Holds all runtime configuration for the dashboard (paths, host, port, retention, etc.). |
| `HomeKpis` | Summary numbers shown above the fold on the home page. |
| `TelemetrySummary` | Aggregated request counts, costs, and savings by workflow and day. |
| `WorkflowEntry` | One entry in the workflow catalog (name, description, stage count, tier map). |
| `Feature` | One feature from `.help/features.yaml`, used by the scope picker. |
| `SpecPhase` | Status snapshot for one phase file within a spec. |

## Configuration

`build_config()` accepts these parameters, all of which fall back to sensible defaults:

| Parameter | Default | Purpose |
|---|---|---|
| `project_root` | current directory | Root of the project being inspected. |
| `host` | `127.0.0.1` | Interface the server binds to. |
| `port` | `8765` | Port the server listens on. |
| `allow_run` | `False` | Enable the workflow run-trigger endpoint. |
| `specs_roots` | `()` | Additional directories to include in the federated spec listing. |
| `trusted_hosts` | `()` | Extra hostnames added to the `Host` header allowlist. |
| `runs_retention_days` | `30` | How many days to keep persisted run files before `prune_old_runs()` removes them. |

The `ATTUNE_OPS_SWEEP_RESULTS` environment variable must be set to a non-empty value to enable sweep-result persistence (`is_persistence_enabled()`).

## Integration patterns

### Building a config and launching the app programmatically

When you want to embed the dashboard inside a larger process rather than use the CLI, build a `Config` explicitly and pass it to `create_app()`. Keep the bind on `127.0.0.1` so the dashboard isn't reachable from outside the local machine:

```python
from pathlib import Path
from attune.ops import build_config, create_app

config = build_config(
    project_root=Path("/path/to/your/project"),
    host="127.0.0.1",
    port=9000,
    allow_run=True,
)

app = create_app(config)

# Hand `app` to any ASGI server, e.g. uvicorn:
import uvicorn
uvicorn.run(app, host=config.host, port=config.port)
```

If you genuinely need to reach the dashboard from another machine, prefer an SSH tunnel (`ssh -L 8765:127.0.0.1:8765 user@host`) or a reverse proxy that handles auth — do not bind the server to `0.0.0.0` directly. The dashboard has no built-in authentication.

### Reading telemetry and KPIs without starting the server

If you only need the dashboard's data layer — for example, to pipe numbers into a CI report — you can call the reader functions directly without launching the HTTP server:

```python
from pathlib import Path
from attune.ops import build_config, read_telemetry_summary, home_kpis

config = build_config(project_root=Path("/path/to/your/project"))

summary = read_telemetry_summary(config.telemetry_path)
kpis = home_kpis(summary)

print(f"Today: {kpis.today_events} events, ${kpis.today_cost:.4f}")
print(f"7-day savings: ${kpis.seven_day_savings:.4f}")
```

## See also

- [Tutorial: ops-dashboard walkthrough](../tutorials/ops-dashboard.md) — end-to-end first run, including the workflow runner and scope picker
- [Reference: ops-dashboard API](../reference/ops-dashboard.md) — full symbol-by-symbol API listing
- [Architecture: ops-dashboard](../architecture/ops-dashboard.md) — how the configuration, FastAPI app, and persistence layers fit together

<!-- attune-generated: source_hash=395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42 feature=ops-dashboard kind=how-to generated_at=2026-05-14 -->
