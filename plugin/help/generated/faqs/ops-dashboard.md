---
name: ops-dashboard
source: content/features/ops-dashboard.md
tags:
- ops
- dashboard
- runner
- workflows
- scope-picker
- persistence
- sse
type: faq
---

# Ops Dashboard FAQ

## What is the ops dashboard?

A local FastAPI web app for running attune workflows against a
feature scope, with persisted run history, workflow chaining, and live
SSE log streaming. Start it with `attune ops` (default
`127.0.0.1:8765`).

## How do I start it?

`attune ops` or `python -m attune.ops`. Runs are enabled by
default; pass `--read-only` for a look-but-don't-run dashboard.

## What's the public API?

Exactly `create_app`, `build_config`, and `Config`
(`attune.ops.__all__`). The runner is `attune.ops.runner`.

## Why won't my workflow run?

`Config.allow_run` must be `True`. It defaults to `False`; the
CLI enables it unless you pass `--read-only`.

## What's async on the runner?

`RunnerService.start()` and `Run.subscribe()`. The history and
lookup helpers (`recent`, `get`, `get_or_load`) are synchronous.

## Can I run two workflows at once?

No — one at a time. A concurrent `start()` raises
`RunnerBusyError`.

## Does it own the cost/telemetry/help data it shows?

No. Those are adjacent surfaces — `ops.data`/
`ops.anthropic_cost`/`ops.help_data` only read data owned by the
telemetry and help-system features.
