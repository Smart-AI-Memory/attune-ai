---
type: concept
name: ops-dashboard-concept
feature: ops-dashboard
depth: concept
generated_at: 2026-06-02T10:56:02.695500+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Ops Dashboard

The ops dashboard is a local web server — launched via `attune ops` or `python -m attune.ops` — that gives you a unified view of your workflow runs, API costs, spec completion candidates, and Claude Code sessions.

## What the dashboard does

The dashboard binds to `127.0.0.1:8765` by default (configurable via `Config.host` and `Config.port`) and exposes a FastAPI application created by `create_app()`. From a single interface you can:

- **Run workflows** with a per-feature scope picker that reads feature definitions from `.help/features.yaml`
- **Stream logs** in real time over SSE as a workflow executes
- **Chain workflows** by clicking through to the next stage from the run result
- **Browse run history** from the directory at `Config.runs_dir`, retained for `Config.runs_retention_days` days (default 30)
- **Review Claude Code sessions** detected heuristically and surfaced on the `/sessions` page
- **Monitor API costs** pulled from the Anthropic admin cost-report endpoint

## How the pieces fit together

Four subsystems feed data into the dashboard's pages:

### Cost reporting

`fetch_summary(refresh=False)` calls the Anthropic admin cost-report API and returns either a `CostSummary` or a `CostFetchError`. `CostSummary` breaks spending down by day (`by_day`), by model (`by_model`), and by cost type (`by_cost_type`), covering today, the last 7 days, month-to-date, and the last 30 days. Results are cached in memory; pass `refresh=True` to bypass the cache. If the admin API key is absent, `load_admin_key()` returns `None` and the cost panel is hidden rather than failing.

`CostFetchError` carries a `kind` field (a `CostFetchErrorKind` value) alongside a human-readable `message`, so the dashboard can show a specific reason — expired key, network failure, and so on — rather than a generic error.

### Spec completion candidates

When `Config.specs_candidates_enabled` is `True`, `detect_candidates(config)` scans the directories listed in `Config.specs_roots` and returns a list of `Candidate` objects. Each `Candidate` records the spec's `slug`, `path`, `current_status`, supporting `evidence`, and a `snapshot_hash` used to suppress dismissed suggestions (stored in `spec_completion_dismissed.json` under the `ops/` subdirectory of `Config.attune_home`).

### Telemetry

`TelemetrySummary` aggregates workflow usage recorded to `Config.telemetry_path`. Its fields cover total requests, total cost, total savings, a per-workflow breakdown (`by_workflow`), and a per-day breakdown (`by_day`). This data powers the usage charts on the dashboard's overview page.

### Configuration

`Config` is the single source of truth for where the dashboard reads and writes state. Key paths derived from its two required fields — `project_root` and `attune_home` — include:

| Property | Purpose |
|---|---|
| `runs_dir` | Root for persisted workflow run output |
| `telemetry_path` | Location of the telemetry event log |
| `sessions_dir` | Storage for detected Claude Code sessions |
| `bulletin_dir` | Active log and archive for the multi-actor bulletin |
| `memory_dir` | Agent memory storage |

Set `Config.allow_run` to `True` to permit the dashboard to actually execute workflows; without it, run requests are accepted but not dispatched.

## When the dashboard matters

The dashboard is most useful when you are running attune workflows repeatedly across multiple features and want visibility into cost trends, which specs are nearing completion, and what a previous run produced — without switching between terminal output and separate reporting tools.
