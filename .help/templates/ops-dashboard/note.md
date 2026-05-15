---
type: note
name: ops-dashboard-note
feature: ops-dashboard
depth: note
generated_at: 2026-05-14T14:43:23.575771+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Note: ops dashboard

## Context

`attune ops` is a local operations dashboard for the workflow OS. It provides a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. You can start it as a CLI command (`attune ops`) or run it directly with `python -m attune.ops`.

## Public API boundary

The package exposes three names at the top level (`__all__ = {'create_app', 'build_config', 'Config'}`), split between data classes and factory functions.

**Data classes** (defined in `src/attune/ops/data.py` and `src/attune/ops/config.py`):

| Class | Purpose |
|---|---|
| `Config` | Holds project root, attune home, server address, and runtime flags. Also exposes computed paths such as `runs_dir`, `memory_dir`, and `sessions_dir`. |
| `TelemetrySummary` | Aggregated request counts, costs, and savings, broken down by workflow and by day. |
| `WorkflowEntry` | Name, description, stage count, and tier map for a single workflow. |
| `PathArgSpec` | Describes how a workflow accepts a scope path argument on the CLI. |
| `Feature` | One entry from `.help/features.yaml`, used to populate the scope picker. |
| `HomeKpis` | Today's event count and cost, seven-day cost and savings, and a sparkline list — shown above the fold on the home page. |

**Factory functions** (defined in `src/attune/ops/__init__.py` and `src/attune/ops/cli.py`):

| Function | Purpose |
|---|---|
| `create_app()` | Lazily imports the FastAPI factory, so importing `attune` does not pull in FastAPI as a side effect. |
| `build_config()` | Constructs a `Config` from explicit arguments and environment defaults, including an env-based attune home override. |
| `add_subparser()` | Registers the `ops` subcommand on the main `attune` CLI parser. |
| `cmd_ops()` | Starts the dashboard server (blocking). Returns `0` on clean exit. |
| `main()` | Standalone entry point for `python -m attune.ops`. |

## Design notes

- **Lazy imports.** `create_app` and `build_config` defer their imports so that `import attune` stays lightweight even when FastAPI is installed.
- **Host allowlist.** `TrustedHostMiddleware` rejects any request whose `Host` header is not in `Config.trusted_hosts`. The default bind address is `127.0.0.1:8765`.
- **Run retention.** Persisted ops runs live under `Config.runs_dir` and are pruned after `runs_retention_days` days (default: 30). The directory is created on first write.
- **Scope picker.** `list_features()` parses `.help/features.yaml` relative to the project root. `first_feature()` returns the alphabetically first entry that has a renderable scope, which the dashboard uses as the default selection.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
