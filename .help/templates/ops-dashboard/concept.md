---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-18T05:24:12.363229+00:00
source_hash: b6ca0aef7a04a6f5122f0108db8941b3fcbbd161578c24f5d23838793ec43ec1
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

Under the hood, this feature spans 42 source
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
