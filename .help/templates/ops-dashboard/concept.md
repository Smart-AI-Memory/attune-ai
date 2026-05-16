---
type: concept
name: ops-dashboard-concept
feature: ops-dashboard
depth: concept
generated_at: 2026-05-16T06:19:45.785146+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Ops Dashboard

The ops dashboard is a local web server that gives you a live view of your attune workflows — showing cost telemetry, session history, and run logs — and lets you trigger workflow runs scoped to a specific feature or path.

## How the pieces fit together

When you run `attune ops` (or `python -m attune.ops`), the CLI builds a `Config` object and starts a FastAPI server bound to `127.0.0.1:8765` by default. Everything the dashboard reads and renders flows through that config:

- **`Config`** anchors the server to your `project_root` and `attune_home`. It also determines where persisted data lives: `runs_dir` holds the history of past workflow executions, `sessions_dir` holds Claude Code session records, and `telemetry_path` points to the cost event log. None of those directories need to exist before first use.
- **`TelemetrySummary`** aggregates the telemetry log into the numbers the dashboard surfaces — total requests, total cost, total savings, a per-workflow breakdown, and a per-day breakdown — so the home page can show you spend at a glance without reading raw event files.
- **`HomeKpis`** and **`DailyCost`** feed the above-the-fold summary: today's event count, today's cost, seven-day cost, seven-day savings, and the sparkline that visualizes daily cost over time.
- **`WorkflowEntry`** describes each workflow the dashboard can run: its name, description, number of stages, and the tier map that governs which model tier each stage uses.
- **`Feature`** represents one entry from `.help/features.yaml`. The scope picker on the workflow runner page lists your project's features so you can target a workflow at a specific part of the codebase rather than running it over everything.
- **`PathArgSpec`** tells the dashboard how a given workflow accepts a path argument on the CLI — which keyword argument to use and whether it is required — so the scope picker can construct the correct invocation.
- **`Session`** represents one Claude Code session as it appears on the `/sessions` page: start time, duration, message count, and an AI-generated starter summary so you can decide whether to resume it.
- **`TrustedHostMiddleware`** rejects any request whose `Host` header is not on the `trusted_hosts` allowlist, keeping the local server from being reachable by unexpected callers even when `allow_run` is enabled.

## When the dashboard matters

The dashboard is most useful in three situations:

1. **Monitoring cost.** `TelemetrySummary` and `HomeKpis` turn raw telemetry events into a readable spend summary. If a workflow is consuming unexpectedly many tokens, the per-workflow breakdown shows it immediately.
2. **Running workflows with a specific scope.** Without the dashboard, you pass a path argument directly on the CLI. With it, the scope picker reads your `.help/features.yaml` via `list_features()` and `first_feature()`, presents your features by name, and constructs the correct invocation — no need to remember argument names or paths.
3. **Reviewing session history.** The `/sessions` page surfaces past Claude Code sessions with AI-generated summaries (produced by the `SUMMARY_PROMPT` logic) so you can orient yourself before resuming work.

## Key configuration options

`build_config()` accepts these values, all of which have defaults so you can start the server with no arguments:

| Option | Default | Effect |
|---|---|---|
| `host` | `127.0.0.1` | Interface the server binds to |
| `port` | `8765` | Port the server listens on |
| `allow_run` | `False` | Whether workflow execution is permitted from the UI |
| `runs_retention_days` | `30` | How many days of run history to keep on disk |
| `specs_roots` | `()` | Additional directories to scan for workflow specs |
| `trusted_hosts` | `()` | Host header allowlist enforced by `TrustedHostMiddleware` |

## Related topics

- **Reference**: Ops dashboard — all `Config` fields, data structures, and CLI flags
- **Quickstart**: Ops dashboard — start the server and run your first scoped workflow
- **Concept**: Template design patterns — how `.help/features.yaml` feature entries are structured
