---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-26T21:24:05.329875+00:00
source_hash: 1e99b94aaa6cb25d1a8177ca5ac28496f3fbd5498c6aea2873c19d7fdab748f0
status: generated
---

# Ops Dashboard

## How it works

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

The main building blocks are:

- **`CostFetchError`** — Categorized failure for cost-report fetch.
- **`CostSummary`** — Account-level cost data from the Anthropic admin cost-report.
- **`Candidate`** — One completion-candidate spec returned by the detector.
- **`Config`** — Where attune ops reads project + attune state from.
- **`TelemetrySummary`** — core component

Under the hood, this feature spans 45 source
files covering:

- Run via ``python -m attune.ops``.
- Anthropic admin cost-report client.
- CLI entrypoint for ``attune ops``.

## What connects to it

This feature relates to: ops, dashboard, runner, workflows, scope-picker, persistence, sse.

Other parts of the codebase interact with
ops dashboard through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `CostFetchError` | Categorized failure for cost-report fetch. | `src/attune/ops/anthropic_cost.py` |
| `CostSummary` | Account-level cost data from the Anthropic admin cost-report. | `src/attune/ops/anthropic_cost.py` |
| `Candidate` | One completion-candidate spec returned by the detector. | `src/attune/ops/completion_candidates.py` |
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | — | `src/attune/ops/data.py` |
