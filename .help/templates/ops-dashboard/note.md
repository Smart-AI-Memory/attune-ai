---
type: note
name: ops-dashboard-note
feature: ops-dashboard
depth: note
generated_at: 2026-05-16T06:19:45.818082+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106bc0edfcc0df951fa4fae4106bc0edfcc0df951fa4fae4106bc0edfcc0df951fa4fae4106ba836
status: generated
---

# Note: ops dashboard

## Context

`attune ops` is a local operations dashboard that combines a workflow runner, a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. It runs as a blocking HTTP server (default `127.0.0.1:8765`) and is reachable via `attune ops` on the CLI or `python -m attune.ops` as a standalone entry point.

## Public surface

The package exports three names at the boundary (`__all__ = {'create_app', 'build_config', 'Config'}`):

| Name | Kind | Source | Role |
|---|---|---|---|
| `Config` | dataclass | `ops/config.py` | Holds every runtime setting the dashboard reads — paths, host/port, retention policy, trusted hosts |
| `create_app` | function | `ops/__init__.py` | Lazy-imports the FastAPI factory; keeps the top-level `attune` import free of FastAPI |
| `build_config` | function | `ops/__init__.py` | Lazy-imports the config builder; constructs a `Config` from CLI args and environment defaults |

Additional internal functions in `ops/cli.py` wire these together:

- `add_subparser()` — registers the `ops` subparser on the main `attune` CLI parser
- `cmd_ops()` — calls `build_config` and `create_app`, then serves the dashboard (blocking, returns `0`)
- `main()` — thin wrapper used by the `python -m attune.ops` entry point

## Data model

The dashboard surfaces read-only data through a set of dataclasses in `ops/data.py`. None of these are mutable by callers.

| Class | What it represents |
|---|---|
| `WorkflowEntry` | A single workflow — name, description, stage count, and tier map |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI (`kwarg`, `required`) |
| `Feature` | One entry from `.help/features.yaml`, used to populate the scope picker |
| `Session` | One Claude Code session surfaced on the `/sessions` page |
| `HomeKpis` | Summary numbers shown above the fold on the home page |
| `TelemetrySummary` | Aggregated request counts, costs, and savings across workflows and days |
| `DailyCost` | One day's cost data, used for the home-page sparkline |
| `FamilyVersion` | Package version info surfaced by the dashboard |

## Security

`TrustedHostMiddleware` (in `ops/`) rejects any request whose `Host` header is not on the `trusted_hosts` allowlist configured in `Config`. The default configuration binds only to `127.0.0.1`, so external exposure requires an explicit host and allowlist change.

## Source files

`src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
