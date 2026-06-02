---
type: comparison
name: ops-dashboard-comparison
feature: ops-dashboard
depth: comparison
generated_at: 2026-06-02T10:56:02.742564+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Comparison: Ops Dashboard vs alternatives

## Context

The ops dashboard (`attune ops` / `python -m attune.ops`) is a local FastAPI server that combines a workflow runner, per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming into a single interface. It is the primary way to operate the attune workflow OS interactively.

## Feature comparison

| Capability | Ops dashboard | Direct API / scripts |
|---|---|---|
| **Workflow execution** | Browser UI with scope picker (`Feature.path`, `Feature.tags`) and clickable chaining between workflow stages | Must wire `WorkflowEntry` stage map and `PathArgSpec` arguments by hand |
| **Cost visibility** | Live Anthropic spend via `fetch_summary()` — today, 7-day, MTD, 30-day, and per-model breakdowns from `CostSummary` | Call `fetch_summary()` yourself and format `CostSummary` fields manually |
| **Run history** | Runs persisted under `Config.runs_dir`; retained for `Config.runs_retention_days` days (default 30) | No persistence; output is ephemeral unless you add it |
| **Session tracking** | `/sessions` page surfaces `Session` records (id, duration, message count, starter prompt) | Not available outside the dashboard server |
| **Spec completion candidates** | Detector runs automatically when `Config.specs_candidates_enabled = True`; surfaces `Candidate` slugs with evidence | Call `detect_candidates(config)` manually and parse results yourself |
| **Telemetry** | `TelemetrySummary` aggregated by workflow and by day; written to `Config.telemetry_path` | Read the raw telemetry file and aggregate yourself |
| **Bulletin / multi-actor log** | Streamed from `Config.bulletin_dir`; visible in the UI without extra tooling | Tail the files in `bulletin_dir` manually |
| **Configuration surface** | Single `Config` dataclass controls host, port, retention, trusted hosts, and spec roots | Must construct `Config` explicitly and pass it through every call |
| **Startup** | `cmd_ops(args)` — blocking; returns `0` on clean exit | `create_app()` returns the FastAPI app for embedding in your own server |

## Tradeoffs

**Ops dashboard strengths**

- Zero boilerplate for the common case: `attune ops` starts the server; `build_config()` resolves all paths from `Config.project_root` and `Config.attune_home`.
- `fetch_summary(refresh=False)` caches results in memory; subsequent calls in the same process are instant. Pass `refresh=True` to force a live fetch from `_COST_REPORT_URL`.
- Run history and session data survive process restarts because they are written to disk (`Config.runs_dir`, `Config.sessions_dir`).
- `Config.allow_run` acts as a safety gate — workflow execution is disabled by default until you opt in.

**Direct API / script strengths**

- `create_app()` lazy-imports FastAPI, so importing `attune` in a script does not pay the FastAPI startup cost unless you actually call it.
- `detect_candidates(config)` can be called standalone (with an optional `now` float for time-travel in tests) without starting the HTTP server.
- `load_admin_key()` and `fetch_summary()` are independently usable if you only need cost data.
- `clear_cache()` is available for test isolation without touching the server.

## Use ops dashboard when…

- You want an interactive view of workflow status, cost, sessions, and spec candidates without writing glue code.
- You need persisted run history across multiple working sessions (`Config.runs_retention_days` controls how far back you can look).
- You are operating on a specific feature and want the scope picker to filter workflows to the right `Feature.path`.
- You need `Config.specs_candidates_enabled = True` to surface spec completion candidates automatically as you work.
- You are sharing a dashboard across a team and need `Config.trusted_hosts` to control access.

## Use the API directly when…

- You are writing a test and need `detect_candidates(config)` or `fetch_summary()` in isolation — the server is unnecessary overhead.
- You are embedding ops capabilities into an existing FastAPI application and want `create_app()` on your own terms.
- You only need Anthropic cost data; `fetch_summary()` plus the `CostSummary` fields (`today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd`, `by_model`) give you everything without starting a server.
- You need a one-off candidate scan; call `detect_candidates(config)` and inspect the `Candidate` fields (`slug`, `current_status`, `evidence`) directly.

**Bottom line:** the ops dashboard is the right default for interactive, day-to-day operation of the workflow OS. The direct API surface is the right choice when you need a single capability in a script or test, or when you are embedding attune into a larger application.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
