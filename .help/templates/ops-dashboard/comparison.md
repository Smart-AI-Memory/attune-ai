---
type: comparison
name: ops-dashboard-comparison
feature: ops-dashboard
depth: comparison
generated_at: 2026-05-16T06:19:45.820558+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Comparison: Ops Dashboard vs alternatives

## Context

The ops dashboard is a local web server (`attune ops` / `python -m attune.ops`) that surfaces workflow execution for a project. Its defining capabilities are a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. It is built on FastAPI and runs on `127.0.0.1:8765` by default.

## Feature comparison

| Capability | Ops dashboard | CLI script | Throwaway script |
|---|---|---|---|
| **Launch** | `attune ops` or `python -m attune.ops` | Any terminal command | Any terminal command |
| **Workflow execution** | Interactive — scope picker drives `PathArgSpec` per workflow | Manual argument passing | Manual argument passing |
| **Run history** | Persisted to disk; retained for `runs_retention_days` (default 30) | None | None |
| **Log streaming** | Live SSE stream in browser | Terminal stdout | Terminal stdout |
| **Session visibility** | `/sessions` page shows Claude Code sessions with duration, message count, and AI-generated resume prompt | None | None |
| **Cost tracking** | Home page KPIs: today's cost, 7-day cost, 7-day savings, per-workflow and per-day breakdowns | None | None |
| **Feature scoping** | Reads `.help/features.yaml`; `first_feature()` sets the default scope on first paint | N/A | N/A |
| **Security** | `TrustedHostMiddleware` enforces `trusted_hosts` allowlist; `allow_run` gates execution | Process-level only | Process-level only |
| **Setup cost** | Requires `build_config()` and a running server process | Zero | Zero |

## Tradeoffs

**Ops dashboard strengths**

- Run history survives process restarts. A throwaway script gives you nothing to look back at; the dashboard keeps `runs_retention_days` days of structured records under `Config.runs_dir`.
- The scope picker removes argument-wiring boilerplate. Workflows that accept a `PathArgSpec` get a UI control automatically — no manual `--path` flags per invocation.
- Cost and telemetry data (`TelemetrySummary`, `HomeKpis`, `DailyCost`) are aggregated and visible without writing any reporting code.
- Session summaries use Claude Haiku to generate a one-sentence resume prompt per session, making it practical to context-switch across many Claude Code sessions in a day.

**Ops dashboard limitations**

- It is a server process. For a one-off task, starting `attune ops` and navigating to a browser is more friction than running a script directly.
- It has no headless or CI mode. `cmd_ops()` blocks; `allow_run=False` by default means workflow execution must be explicitly enabled. It is not designed for unattended pipeline use.
- The public API surface is intentionally narrow: `create_app`, `build_config`, and `Config` are the only exported names. Behavior not exposed through those three should not be patched internally.

## Use the ops dashboard when

- You are running workflows repeatedly across multiple features and want a scope picker rather than hand-typing path arguments each time.
- You need to review or compare past runs — cost, duration, or log output — without instrumenting anything yourself.
- You are managing multiple Claude Code sessions and want AI-generated summaries to decide which to resume.
- You want cost and savings telemetry (`seven_day_cost`, `seven_day_savings`) aggregated without writing reporting code.

## Skip the ops dashboard when

- You are running a workflow once, or writing a throwaway script to explore an idea. A direct CLI invocation has zero setup cost.
- You need the workflow to run in CI or another unattended context. The dashboard's blocking server model and browser-first UX are not a fit for pipelines.
- Your problem spans multiple features and needs orchestration above the dashboard layer — call the orchestration layer directly rather than routing through the dashboard server.
- You need behavior that `create_app`, `build_config`, or `Config` do not expose. File an issue or propose an extension point rather than reaching into unexported internals.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
