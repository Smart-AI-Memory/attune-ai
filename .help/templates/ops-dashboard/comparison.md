---
type: comparison
name: ops-dashboard-comparison
feature: ops-dashboard
depth: comparison
generated_at: 2026-06-10T07:07:04.679153+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Comparison: Ops Dashboard vs alternatives

## Context

The ops dashboard (`attune ops` / `python -m attune.ops`) is a local server that combines a workflow runner, per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming into a single interface. It exposes a FastAPI application via `create_app()` and reads project and attune state through a `Config` dataclass.

## Feature comparison

| Capability | Ops dashboard | Ad-hoc script | Direct CLI invocation |
|---|---|---|---|
| **Workflow execution** | Full — scope picker, `WorkflowEntry` stage map, workflow chaining | Manual — you wire the calls yourself | Single workflow only, no chaining |
| **Run history** | Persisted to `Config.runs_dir`; retained for `runs_retention_days` days (default 30) | None unless you add it yourself | None |
| **Cost visibility** | Live Anthropic cost report via `fetch_summary()` with `CostSummary` fields (`today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd`, `by_model`) | None | None |
| **Session tracking** | `Session` records surfaced on `/sessions` page (message count, duration, starter prompt) | None | None |
| **Spec completion candidates** | Detected via `detect_candidates()` when `specs_candidates_enabled = True` | None | None |
| **Scope targeting** | Feature-level via `.help/features.yaml` `Feature` entries and `PathArgSpec` | Hardcoded paths | Single `--path` argument at most |
| **Telemetry** | `TelemetrySummary` tracks requests, cost, savings, and per-workflow breakdowns | None | None |
| **Startup overhead** | FastAPI server + SSE — not suitable for quick one-off commands | Near-zero | Near-zero |
| **Remote access** | Configurable `host`/`port`; `trusted_hosts` whitelist | N/A | N/A |
| **Admin API key required** | Yes, for `fetch_summary()` — `load_admin_key()` returns `None` if unavailable; cost panel is skipped gracefully | N/A | N/A |

## Tradeoffs

**Ops dashboard wins when** you need any combination of: cross-workflow visibility, cost tracking, session history, or scope-targeted execution. All of that infrastructure is built in and requires no extra code on your part.

**Ops dashboard loses when** you need a fast, stateless command. The server starts on `host:port` (default `127.0.0.1:8765`) and blocks (`cmd_ops()` returns `0` only on clean shutdown). For a single workflow run with no need for history or cost data, launching the full server is unnecessary overhead.

**Cost data is optional, not required.** `fetch_summary(refresh=False)` returns a `(CostSummary | None, CostFetchError | None)` tuple. If `load_admin_key()` returns `None`, the dashboard still runs — cost panels are simply absent. You do not need Anthropic admin credentials to use the workflow runner.

**`allow_run`** defaults to `False` in `Config`. The dashboard can display workflow metadata without being allowed to execute runs. This is the safe default for read-only inspection.

## When to use the ops dashboard

Use the ops dashboard when at least one of these is true:

- You are running multiple workflows against different features and want a scope picker rather than manually specifying paths on every invocation.
- You need to inspect run history across sessions — `Config.runs_dir` and `runs_retention_days` give you durable records without any extra tooling.
- You want live Anthropic cost data (`CostSummary.today_usd`, `by_model`, etc.) visible alongside your workflow activity.
- You are working on a project with spec completion tracking and want `detect_candidates()` surfaced automatically (`specs_candidates_enabled = True`).
- You want clickable workflow chaining — advancing from one `WorkflowEntry` stage to the next without returning to the terminal.

## When to use an alternative instead

- **Single, quick command with no history needed:** invoke the workflow directly via the `attune` CLI. The ops dashboard's server startup and SSE infrastructure add latency that a one-shot command does not justify.
- **Automated or CI context:** a blocking server (`cmd_ops`) is the wrong shape for a pipeline step. Call the relevant function directly or use the CLI subcommand in a non-interactive script.
- **Exploratory or throwaway work:** a small script that calls the relevant functions directly is simpler than standing up a dashboard you will discard.
- **You need behavior not exposed in `__all__`** (`create_app`, `build_config`, `Config`): do not reach into private internals — the surface is intentionally narrow. File an issue or propose an extension point instead.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
