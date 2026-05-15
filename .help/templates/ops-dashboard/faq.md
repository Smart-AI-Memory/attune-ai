---
type: faq
name: ops-dashboard-faq
feature: ops-dashboard
depth: faq
generated_at: 2026-05-14T14:43:23.569106+00:00
source_hash: 395f221f9a789d9b8851995c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Ops Dashboard FAQ

## What is the ops dashboard?

The ops dashboard is a local web server that lets you run workflows against a specific feature scope, stream live logs over SSE, and browse persisted run history — all from a browser UI. Start it with `attune ops` or `python -m attune.ops`.

## When should I use it?

Use the ops dashboard when you want to run and monitor attune workflows locally — for example, to pick a feature scope, chain workflows together by clicking through the UI, or review past run history. If you're looking to automate runs non-interactively, check the other features listed in your project's `.help/features.yaml`.

## What's the main entry point?

Run the server with the `attune ops` CLI command. Under the hood this calls `cmd_ops()`, which is blocking. The three public symbols you're most likely to use directly are:

- `create_app()` — constructs the FastAPI application (lazy-imported so that importing `attune` doesn't pull in FastAPI)
- `build_config()` — builds a `Config` from your inputs and environment defaults (host, port, `allow_run`, retention days, etc.)
- `Config` — the dataclass that controls where the dashboard reads project and attune state from

## How do I configure the server?

Pass arguments to `build_config()`, or let it pick up environment defaults. The key fields on `Config` are:

| Field | Default | What it controls |
|---|---|---|
| `host` | `127.0.0.1` | Interface the server binds to |
| `port` | `8765` | Port the server listens on |
| `allow_run` | `False` | Whether the dashboard can trigger workflow runs |
| `trusted_hosts` | `()` | Allowlist checked by `TrustedHostMiddleware` |
| `runs_retention_days` | `30` | How long persisted run history is kept |

## Where does the dashboard store its data?

All data lives under the paths exposed by `Config`:

- **Telemetry** — `Config.telemetry_path`
- **Run history** — `Config.runs_dir` (created on first write)
- **Memory** — `Config.memory_dir`
- **Sessions** — `Config.sessions_dir`

## How do I debug it?

Run the related tests first with `pytest -k "ops-dashboard" -v`. If the tests pass but your code still fails, add a `logger.debug` call at the suspected failure point and re-run with logging enabled. For symptom-based diagnosis, see the troubleshooting page for this feature.

## Where are the source files?

All ops dashboard source files are under `src/attune/ops/`.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
