---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-17T18:28:27.048023+00:00
source_hash: 848a51e7aabcd39ac987255bff940539153d7b544651bdec566acd763432d775
status: generated
---

# Ops Dashboard

## How it works

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

The main building blocks are:

- **`Candidate`** — One completion-candidate spec returned by the detector.
- **`Config`** — Where attune ops reads project + attune state from.
- **`TelemetrySummary`** — core component
- **`WorkflowEntry`** — core component
- **`PathArgSpec`** — How a workflow accepts a scope path on the CLI.

Under the hood, this feature spans 40 source
files covering:

- Run via ``python -m attune.ops``.
- CLI entrypoint for ``attune ops``.
- Detector for spec completion candidates.

## What connects to it

This feature relates to: ops, dashboard, runner, workflows, scope-picker, persistence, sse.

Other parts of the codebase interact with
ops dashboard through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `Candidate` | One completion-candidate spec returned by the detector. | `src/attune/ops/completion_candidates.py` |
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | — | `src/attune/ops/data.py` |
| `WorkflowEntry` | — | `src/attune/ops/data.py` |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. | `src/attune/ops/data.py` |
