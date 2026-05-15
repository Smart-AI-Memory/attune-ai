---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-15T11:24:19.636240+00:00
source_hash: 55ce9290506b249ccc67bc94cb823e906686e4c1c3e8534a515406908f54aedf
status: generated
---

# Ops Dashboard

## How it works

Local operations dashboard — workflow runner with per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

The main building blocks are:

- **`Config`** — Where attune ops reads project + attune state from.
- **`TelemetrySummary`** — core component
- **`WorkflowEntry`** — core component
- **`PathArgSpec`** — How a workflow accepts a scope path on the CLI.
- **`Feature`** — One feature from ``.help/features.yaml`` for the scope picker.

Under the hood, this feature spans 30 source
files covering:

- Run via ``python -m attune.ops``.
- CLI entrypoint for ``attune ops``.
- Runtime configuration for attune ops.

## What connects to it

This feature relates to: ops, dashboard, runner, workflows, scope-picker, persistence, sse.

Other parts of the codebase interact with
ops dashboard through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | — | `src/attune/ops/data.py` |
| `WorkflowEntry` | — | `src/attune/ops/data.py` |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. | `src/attune/ops/data.py` |
| `Feature` | One feature from ``.help/features.yaml`` for the scope picker. | `src/attune/ops/data.py` |
