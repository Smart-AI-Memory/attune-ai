---
type: concept
name: ops-dashboard-concept
feature: ops-dashboard
depth: concept
generated_at: 2026-06-10T07:07:04.642397+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Ops Dashboard

## What the ops dashboard is

The ops dashboard is a locally running web server — the operations layer of the attune workflow OS — that lets you run workflows against a specific feature scope, browse persisted run history, chain workflows with a single click, and stream live logs over SSE.

You start it with `attune ops` (or `python -m attune.ops`). It binds to `127.0.0.1:8765` by default and serves a browser UI backed by a FastAPI application created by `create_app`.

## How the pieces fit together

The dashboard is built from four cooperating concerns: configuration, cost reporting, telemetry, and spec-completion detection.

**Configuration** is the root. `Config` tells every other part of the dashboard where to look for project state and attune state:

- `project_root` and `attune_home` anchor all relative paths.
- Derived properties — `runs_dir`, `sessions_dir`, `bulletin_dir`, `memory_dir`, `telemetry_path` — point to the directories where the dashboard reads and writes persisted data.
- `specs_roots` lists the directories that the candidate detector scans.
- `allow_run` must be `True` before the dashboard will actually execute a workflow; this is a deliberate safety gate.
- `trusted_hosts` restricts which remote hosts may connect.
- `runs_retention_days` (default `30`) controls how long run history is kept on disk.

**Cost reporting** calls the Anthropic admin cost-report endpoint at `https://api.anthropic.com/v1/organizations/cost_report`. `fetch_summary(refresh=False)` returns either a `CostSummary` or a `CostFetchError`. `CostSummary` breaks spending down along three axes — `by_day`, `by_model`, and `by_cost_type` — plus rolled-up totals (`today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd`). The `source` field tells you whether the data came from a live API call or an in-memory cache. When the fetch fails, `CostFetchError` carries a `kind` (a `CostFetchErrorKind` enum) and a human-readable `message` so the UI can display a precise error rather than a generic one.

**Telemetry** is recorded locally. `TelemetrySummary` aggregates the requests the dashboard has processed: `total_requests`, `total_cost`, `total_savings`, and breakdowns `by_workflow` and `by_day`. The UI uses this data to show you which workflows you run most and what they cost.

**Spec-completion detection** is opt-in (`specs_candidates_enabled` in `Config`). When enabled, `detect_candidates` scans the configured `specs_roots` and returns a list of `Candidate` objects — one per spec that looks ready to close out. Each `Candidate` carries the spec's `slug`, `path`, `current_status`, supporting `evidence`, and a `snapshot_hash` so the detector can avoid re-surfacing a candidate you have already dismissed.

## Scope picker and session tracking

The dashboard's feature scope picker reads from `.help/features.yaml`. Each `Feature` entry has a `name`, `description`, optional `path`, and `tags`. When you select a scope, the dashboard filters the workflow list and records the interaction (the `scope_picker_change` event is one of the tracked `EVENTS`, alongside `pill_click` and `rec_card_click`).

Sessions — individual Claude Code conversations — surface on the `/sessions` page. Each `Session` record captures `started_at`, `last_activity`, `duration_seconds`, `message_count`, and the `starter_prompt` that opened the conversation.

## When this matters

You need the ops dashboard when you want to:

- Track Anthropic API spend across models and days without leaving your project.
- Run attune workflows from a browser UI rather than typing CLI commands, especially when you want to chain multiple workflows in sequence.
- Review persisted run history beyond the `runs_retention_days` window to audit what ran and when.
- Let the spec-completion detector surface specs that have accumulated enough evidence to close.

If you only need a single workflow run from the command line and have no interest in the browser UI, the dashboard is more than you need — individual workflows can still be invoked directly through the `attune` CLI without starting the server.
