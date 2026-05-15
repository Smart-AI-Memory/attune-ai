---
type: comparison
name: ops-dashboard-comparison
feature: ops-dashboard
depth: comparison
generated_at: 2026-05-14T14:43:23.578213+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Comparison: Ops Dashboard vs alternatives

## Context

The ops dashboard is a locally-running web server (`attune ops` / `python -m attune.ops`) that combines four capabilities in one place: a per-feature scope picker backed by `.help/features.yaml`, a workflow runner with clickable stage chaining, persisted run history with configurable retention, and live SSE log streaming. Understanding what it does — and what it deliberately does not do — helps you decide whether to start it up or use a lighter alternative.

## Feature comparison

| Capability | Ops dashboard | Ad-hoc script | Direct CLI workflow invocation |
|---|---|---|---|
| **Scope picker UI** | Yes — reads `features.yaml`, resolves `Feature.path` per entry | Manual — you pass paths by hand | No — path is a positional argument |
| **Run history & retention** | Persisted to `runs_dir`; configurable via `runs_retention_days` (default 30 days) | None unless you add it yourself | None |
| **Live log streaming** | Server-sent events (SSE) pushed to the browser | Stdout only | Stdout only |
| **Clickable workflow chaining** | Yes — next-stage links rendered in the UI | No | No |
| **Telemetry & KPIs** | `HomeKpis` surfaced above the fold: today's events, cost, 7-day savings, sparkline | None | None |
| **Host/port control** | `--host` / `--port`; default `127.0.0.1:8765` | N/A | N/A |
| **Trusted-host enforcement** | `TrustedHostMiddleware` rejects unlisted `Host` headers | N/A | N/A |
| **Workflow execution** | Only when `allow_run=True` (off by default) | Full control | Full control |
| **Startup overhead** | FastAPI import deferred via `create_app()` lazy loader; still a server process | Near-zero | Near-zero |
| **Best for** | Interactive, repeated work across multiple features | One-off or CI automation | Single workflow, no UI needed |

## Tradeoffs to weigh

**Ops dashboard is stronger when:**

- You switch between features frequently and the scope picker saves you from re-typing paths every time.
- You want a persistent record of what ran, when it ran, and how much it cost — without building that bookkeeping yourself.
- You need to observe long-running workflow stages in real time through SSE, rather than tailing a log file.
- Telemetry summaries (`TelemetrySummary`, `HomeKpis`) matter to your team.

**Ops dashboard is weaker when:**

- You are running a single workflow once (for example, in CI). Starting a server process, binding a port, and configuring `trusted_hosts` is more ceremony than the job warrants.
- You need `allow_run=True` in an automated context — the flag exists but is off by default precisely because remote execution carries risk; a direct CLI call is safer and more auditable.
- You are doing exploratory, throwaway work. Wiring up `build_config()` and launching the server for a single invocation adds friction that a plain script avoids.
- Your environment cannot expose a local port, or `TrustedHostMiddleware` conflicts with your network setup.

## Deciding which entry point to use

When you have decided to use the dashboard, there are two equivalent entry points:

| Entry point | Use when |
|---|---|
| `attune ops` (via `add_subparser`) | You are already using the `attune` CLI for other subcommands |
| `python -m attune.ops` (`main()`) | You want to launch the dashboard standalone, without the full `attune` CLI context |

Both call `cmd_ops()`, which blocks until the server exits and returns `0`.

## Use the ops dashboard when…

- **You work interactively across multiple features day-to-day.** The scope picker, run history, and telemetry KPIs compound in value the more you use the dashboard — they are not worth the setup cost for a single run.
- **You need live feedback on long workflow stages.** SSE streaming is the ops dashboard's clearest advantage over any CLI alternative; nothing else in this project surfaces real-time stage output in a browser.
- **Run history matters.** If you or your team ever ask "what ran last Tuesday and what did it cost?", the persisted `runs_dir` with `runs_retention_days` is the only option here that answers that question without custom instrumentation.

Skip the ops dashboard and invoke workflows directly when the job is automated, one-shot, or running in an environment where a local web server is impractical.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
