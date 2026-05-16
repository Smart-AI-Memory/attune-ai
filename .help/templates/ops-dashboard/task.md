---
type: task
name: ops-dashboard-task
feature: ops-dashboard
depth: task
generated_at: 2026-05-16T06:19:45.791431+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Work with the ops dashboard

Use the ops dashboard when you need to start, configure, or extend the local operations dashboard — a workflow runner with a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming.

## Prerequisites

- Read access to `src/attune/ops/`
- The `attune` CLI installed and on your `PATH`

## Steps

1. **Identify the entry point that owns the behavior you want to change.**

   The dashboard is split across three modules. Match your goal to the responsible function:

   | Goal | Function | File |
   |---|---|---|
   | Change how the FastAPI app is constructed | `create_app()` | `src/attune/ops/__init__.py` |
   | Change host, port, or retention defaults | `build_config()` | `src/attune/ops/config.py` |
   | Add or rename a CLI flag | `add_subparser()` | `src/attune/ops/cli.py` |
   | Change server startup behavior | `cmd_ops()` | `src/attune/ops/cli.py` |
   | Change the standalone module entry point | `main()` | `src/attune/ops/cli.py` |
   | Change how the attune home directory is resolved | `attune_home()` | `src/attune/ops/config.py` |
   | Change how features are loaded for the scope picker | `list_features()` | `src/attune/ops/data.py` |

2. **Read the function's docstring, parameters, and return type** before editing. Confirm the function owns the behavior end-to-end — some behavior spans `build_config()` in both `__init__.py` (a lazy re-export) and `config.py` (the real implementation).

3. **Edit the target function.** Keep changes consistent with the module's naming conventions, error-handling style, and logging patterns. For example:
   - `build_config()` resolves paths against `project_root` and `attune_home`; pass `Path` objects, not raw strings.
   - `TrustedHostMiddleware` reads `trusted_hosts` from `Config`; update `Config.trusted_hosts` if you need to change the allowlist.
   - `list_features()` reads `<project_root>/.help/features.yaml`; changes to feature loading belong there, not in the app factory.

4. **Start the dashboard and verify your change.**

   Run the server locally:

   ```bash
   attune ops
   ```

   Or run it as a standalone module:

   ```bash
   python -m attune.ops
   ```

   The server binds to `127.0.0.1:8765` by default. Open `http://127.0.0.1:8765` in a browser and confirm the dashboard loads and your change behaves as expected.

5. **Run the test suite** to catch regressions before they reach other developers:

   ```bash
   pytest -k "ops"
   ```

## Verify success

The task is complete when:

- `attune ops` starts without errors and the terminal shows the server address.
- The dashboard home page loads in your browser and displays the KPI summary (today's events, cost, and the 7-day sparkline).
- `pytest -k "ops"` passes with no new failures.
