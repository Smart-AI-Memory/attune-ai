---
feature: ops-dashboard
depth: reference
generated_at: 2026-05-14T14:00:01.194125+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Ops Dashboard reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | — | `src/attune/ops/data.py` |
| `WorkflowEntry` | — | `src/attune/ops/data.py` |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. | `src/attune/ops/data.py` |
| `Feature` | One feature from ``.help/features.yaml`` for the scope picker. | `src/attune/ops/data.py` |
| `FamilyVersion` | — | `src/attune/ops/data.py` |
| `DailyCost` | One day's cost for the home-page sparkline. | `src/attune/ops/data.py` |
| `HomeKpis` | Summary numbers shown above the fold on the home page. | `src/attune/ops/data.py` |
| `TrustedHostMiddleware` | Reject requests whose ``Host`` header isn't on the allowlist. | `src/attune/ops/middleware.py` |
| `SpecPhase` | One phase file's status snapshot. | `src/attune/ops/routes/specs.py` |
| `SpecRecord` | One spec's summary — directory + status of each phase file present. | `src/attune/ops/routes/specs.py` |
| `RunnerBusyError` | Raised when a run is already pending/running. | `src/attune/ops/runner.py` |
| `Run` | Single workflow execution + its broadcast state. | `src/attune/ops/runner.py` |
| `RunnerService` | Owns the run history + concurrency lock. | `src/attune/ops/runner.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `create_app()` | Lazy-import the FastAPI factory so importing attune doesn't pull FastAPI. | `src/attune/ops/__init__.py` |
| `build_config()` | Lazy import of the config builder. | `src/attune/ops/__init__.py` |
| `add_subparser()` | Register the `ops` subparser on the main attune CLI parser. | `src/attune/ops/cli.py` |
| `cmd_ops()` | Run the dashboard server (blocking). | `src/attune/ops/cli.py` |
| `main()` | Standalone entry: ``python -m attune.ops``. | `src/attune/ops/cli.py` |
| `attune_home()` | Resolve the user's attune home dir (env override -> ~/.attune). | `src/attune/ops/config.py` |
| `build_config()` | Build a Config from inputs and environment defaults. | `src/attune/ops/config.py` |
| `list_features()` | Return features parsed from ``<project_root>/.help/features.yaml``. | `src/attune/ops/data.py` |
| `first_feature()` | Return the alphabetically-first feature with a renderable scope. | `src/attune/ops/data.py` |
| `home_kpis()` | Derive home-page KPIs from a telemetry summary. | `src/attune/ops/data.py` |
| `sparkline_points()` | Render values as an SVG ``polyline`` ``points`` string. | `src/attune/ops/data.py` |
| `read_telemetry_summary()` | Aggregate ``usage.jsonl`` into a UI-friendly summary. | `src/attune/ops/data.py` |
| `list_workflows()` | Return the registered workflow catalog. Empty if the registry is unavailable. | `src/attune/ops/data.py` |
| `family_versions()` | Resolve installed versions for every related attune package. | `src/attune/ops/data.py` |
| `env_health()` | Lightweight environment snapshot for the Health page. | `src/attune/ops/data.py` |
| `compute_allowlist()` | Compute the default + user-supplied Host allowlist. | `src/attune/ops/middleware.py` |
| `home()` | — | `src/attune/ops/routes/dashboard.py` |
| `workflows_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `telemetry_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `health_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `run_view_page()` | Full-page view for one workflow run. | `src/attune/ops/routes/dashboard.py` |
| `specs_page()` | Specs tab — federated listing of all specs across configured roots. | `src/attune/ops/routes/dashboard.py` |
| `spec_detail_page()` | Drill-in for a single spec: show every phase file's content (read-only). | `src/attune/ops/routes/dashboard.py` |
| `start_run()` | — | `src/attune/ops/routes/runner.py` |
| `get_run()` | — | `src/attune/ops/routes/runner.py` |
| `stream_run()` | — | `src/attune/ops/routes/runner.py` |
| `list_runs()` | Return up to 20 newest runs for ``workflow``, newest first. | `src/attune/ops/routes/runs_history.py` |
| `get_run_record()` | Return one persisted run record (metadata + log). | `src/attune/ops/routes/runs_history.py` |
| `list_specs()` | Federated listing across all configured spec roots. | `src/attune/ops/routes/specs.py` |
| `get_spec()` | Return phase-file contents for one spec. | `src/attune/ops/routes/specs.py` |
| `update_phase_status()` | Rewrite the ``**Status**`` line in the named phase file. | `src/attune/ops/routes/specs.py` |
| `get_sweep_result()` | Return the latest sweep result for a scope-hash, or 404. | `src/attune/ops/routes/sweep_results.py` |
| `echo_command_builder()` | Test helper: produce a portable subprocess that prints two lines + exits 0. | `src/attune/ops/runner.py` |
| `prune_old_runs()` | Delete persisted run files older than ``days``. Returns the deletion count. | `src/attune/ops/runner.py` |
| `create_app()` | Build the FastAPI app, wiring config + templates into request state. | `src/attune/ops/server.py` |
| `is_persistence_enabled()` | True when ``ATTUNE_OPS_SWEEP_RESULTS`` is set to a non-empty value. | `src/attune/ops/sweep_results.py` |
| `results_dir()` | Return ``<attune_home>/ops/sweep-results/`` (created if missing). | `src/attune/ops/sweep_results.py` |
| `scope_hash()` | Hash a scope path to a fixed-length hex identifier. | `src/attune/ops/sweep_results.py` |
| `parse_lines()` | Parse a captured stdout buffer into the final SweepResult JSON. | `src/attune/ops/sweep_results.py` |
| `persist_result()` | Atomically write ``sweep_result`` to ``<results_dir>/<hash>.json``. | `src/attune/ops/sweep_results.py` |
| `read_result()` | Read a previously-persisted result by its scope-hash digest. | `src/attune/ops/sweep_results.py` |
| `persist_from_lines()` | Parse captured stdout lines and persist the result for ``scope_path``. | `src/attune/ops/sweep_results.py` |
| `watch_and_persist()` | Subscribe to a discovery-sweep run; persist its result on success. | `src/attune/ops/sweep_results_watcher.py` |


## Source files

- `src/attune/ops/**`

## Tags

`ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
