---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-31T20:54:22.227361+00:00
source_hash: 55d4ceccfe9282d44ea02ca06378d8a89b8516f920509ddb31a006d0c5d2adb5
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

Under the hood, this feature spans 56 source
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
