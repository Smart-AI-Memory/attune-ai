---
feature: ops-dashboard
depth: concept
generated_at: 2026-05-16T02:33:13.007361+00:00
source_hash: 3847cb81bf0f98356695799e284a8b9b602fccfe6225cd45d19f8f054d716b7e
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

Under the hood, this feature spans 34 source
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
