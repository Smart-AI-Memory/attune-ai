---
type: faq
name: ops-dashboard-faq
feature: ops-dashboard
depth: faq
generated_at: 2026-05-16T06:19:45.811176+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Ops Dashboard FAQ

## What is the ops dashboard?

The ops dashboard is a local web UI for running attune workflows. It provides a per-feature scope picker, persisted run history, clickable workflow chaining, and live log streaming over SSE. You start it with `attune ops` or `python -m attune.ops`.

## How do I start the dashboard?

Run `attune ops` from your project root. By default the server binds to `127.0.0.1:8765`. To change the host, port, or other settings, pass flags on the CLI or call `build_config()` directly.

## What does `allow_run` do?

`allow_run` is a `Config` field that controls whether the dashboard is permitted to execute workflows. It defaults to `False`, so the UI is read-only unless you explicitly enable it.

## How do I change the host or port?

Pass `--host` and `--port` when you run `attune ops`, or construct a `Config` manually using `build_config(host=..., port=...)`. The defaults are `127.0.0.1` and `8765`.

## What is `trusted_hosts` and when do I need it?

`trusted_hosts` is a tuple of hostnames the `TrustedHostMiddleware` allows through. Requests whose `Host` header isn't on the list are rejected. You only need to set this if you expose the dashboard on a non-loopback address.

## Where does the dashboard look for workflows and features?

- **Features** — parsed from `<project_root>/.help/features.yaml` by `list_features()`.
- **Workflow specs** — discovered under the paths in `Config.specs_roots`.

## What shows up on the home page?

The home page displays `HomeKpis`: today's event count, today's cost, seven-day cost, seven-day savings, and a daily cost sparkline. These numbers come from the telemetry log at `Config.telemetry_path`.

## How long is run history kept?

Persisted runs are stored under `Config.runs_dir` and retained for `runs_retention_days` days (default: 30). You can change the retention window via `build_config(runs_retention_days=...)`.

## What appears on the `/sessions` page?

Each entry is a `Session` — a recorded Claude Code session with its start time, duration, message count, and an AI-generated starter summary you can use to decide whether to resume it.

## How do I debug the dashboard when something goes wrong?

Run the related tests first: `pytest -k "ops-dashboard" -v`. If they pass but the dashboard still misbehaves, add a `logger.debug` call at the suspected failure point and re-run with logging enabled. For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where is the source code?

All ops dashboard source lives under `src/attune/ops/`. The three public exports are `create_app`, `build_config`, and `Config` (see `__all__`).

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
