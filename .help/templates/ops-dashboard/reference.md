---
feature: ops-dashboard
depth: reference
generated_at: 2026-05-18T06:14:20.182798+00:00
source_hash: aecb598ac46d567e49df6b1a4fed89b7135aba842be368103ed4fbec7cc451e8
status: generated
---

# Ops Dashboard reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `CostFetchError` | Categorized failure for cost-report fetch. | `src/attune/ops/anthropic_cost.py` |
| `CostSummary` | Account-level cost data from the Anthropic admin cost-report. | `src/attune/ops/anthropic_cost.py` |
| `Candidate` | One completion-candidate spec returned by the detector. | `src/attune/ops/completion_candidates.py` |
| `Config` | Where attune ops reads project + attune state from. | `src/attune/ops/config.py` |
| `TelemetrySummary` | — | `src/attune/ops/data.py` |
| `WorkflowEntry` | — | `src/attune/ops/data.py` |
| `PathArgSpec` | How a workflow accepts a scope path on the CLI. | `src/attune/ops/data.py` |
| `Feature` | One feature from ``.help/features.yaml`` for the scope picker. | `src/attune/ops/data.py` |
| `Session` | One Claude Code session — what surfaces on the dashboard's /sessions page. | `src/attune/ops/data.py` |
| `FamilyVersion` | — | `src/attune/ops/data.py` |
| `DailyCost` | One day's cost for the home-page sparkline. | `src/attune/ops/data.py` |
| `HomeKpis` | Summary numbers shown above the fold on the home page. | `src/attune/ops/data.py` |
| `SweepChipCounts` | Per-bucket counts loaded from a persisted discovery-sweep result. | `src/attune/ops/data.py` |
| `DismissEntry` | One dismissed candidate's persisted state. | `src/attune/ops/dismiss_store.py` |
| `TrustedHostMiddleware` | Reject requests whose ``Host`` header isn't on the allowlist. | `src/attune/ops/middleware.py` |
| `SpecPhase` | One phase file's status snapshot. | `src/attune/ops/routes/specs.py` |
| `SpecRecord` | One spec's summary — directory + status of each phase file present. | `src/attune/ops/routes/specs.py` |
| `RunnerBusyError` | Raised when a run is already pending/running. | `src/attune/ops/runner.py` |
| `Run` | Single workflow execution + its broadcast state. | `src/attune/ops/runner.py` |
| `RunnerService` | Owns the run history + concurrency lock. | `src/attune/ops/runner.py` |
| `RedactionResult` | Outcome of a redaction pass. | `src/attune/ops/session_redaction.py` |
| `SummaryResult` | One Haiku-or-cache result, ready to slot into a :class:`Session`. | `src/attune/ops/session_summarizer.py` |
| `Budget` | Mutable spend ledger for one page-load summarization loop. | `src/attune/ops/session_summarizer.py` |
| `CacheKey` | Stable key that invalidates a cached summary when the source moves. | `src/attune/ops/session_summary_cache.py` |
| `CachedSummary` | One persisted session summary plus the metadata to validate it. | `src/attune/ops/session_summary_cache.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `create_app()` | Lazy-import the FastAPI factory so importing attune doesn't pull FastAPI. | `src/attune/ops/__init__.py` |
| `build_config()` | Lazy import of the config builder. | `src/attune/ops/__init__.py` |
| `clear_cache()` | Empty the in-memory cache. Test-only convenience. | `src/attune/ops/anthropic_cost.py` |
| `load_admin_key()` | Return the admin API key, or ``None`` if unavailable. | `src/attune/ops/anthropic_cost.py` |
| `fetch_summary()` | Return the current cost summary or a categorized error. | `src/attune/ops/anthropic_cost.py` |
| `add_subparser()` | Register the `ops` subparser on the main attune CLI parser. | `src/attune/ops/cli.py` |
| `cmd_ops()` | Run the dashboard server (blocking). | `src/attune/ops/cli.py` |
| `main()` | Standalone entry: ``python -m attune.ops``. | `src/attune/ops/cli.py` |
| `clear_cache()` | Reset the in-memory caches. Test helper. | `src/attune/ops/completion_candidates.py` |
| `detect_candidates()` | Return all completion candidates across the configured spec roots. | `src/attune/ops/completion_candidates.py` |
| `attune_home()` | Resolve the user's attune home dir (env override -> ~/.attune). | `src/attune/ops/config.py` |
| `build_config()` | Build a Config from inputs and environment defaults. | `src/attune/ops/config.py` |
| `list_features()` | Return features parsed from ``<project_root>/.help/features.yaml``. | `src/attune/ops/data.py` |
| `first_feature()` | Return the alphabetically-first feature with a renderable scope. | `src/attune/ops/data.py` |
| `workflow_default_scope()` | Return the default scope for one workflow on first paint. | `src/attune/ops/data.py` |
| `derive_project_name()` | Return a human-readable project name for the dashboard header. | `src/attune/ops/data.py` |
| `claude_sessions_dir()` | Return the canonical directory Claude Code stores sessions for this project in. | `src/attune/ops/data.py` |
| `enumerate_project_encoded_keys()` | Return all ``~/.claude/projects/`` dirs belonging to this logical project. | `src/attune/ops/data.py` |
| `list_recent_sessions_with_paths()` | Same as :func:`list_recent_sessions` but also returns each | `src/attune/ops/data.py` |
| `list_recent_sessions()` | Return Session records for this project's last ``days`` of activity. | `src/attune/ops/data.py` |
| `home_kpis()` | Derive home-page KPIs from a telemetry summary. | `src/attune/ops/data.py` |
| `sparkline_points()` | Render values as an SVG ``polyline`` ``points`` string. | `src/attune/ops/data.py` |
| `read_telemetry_summary()` | Aggregate ``usage.jsonl`` into a UI-friendly summary. | `src/attune/ops/data.py` |
| `read_sweep_chip_counts()` | Read the latest persisted sweep result for ``scope_path`` and tally chips. | `src/attune/ops/data.py` |
| `list_workflows()` | Return the registered workflow catalog. Empty if the registry is unavailable. | `src/attune/ops/data.py` |
| `family_versions()` | Resolve installed versions for every related attune package. | `src/attune/ops/data.py` |
| `env_health()` | Lightweight environment snapshot for the Health page. | `src/attune/ops/data.py` |
| `store_path()` | Return the absolute path to the dismiss-store JSON file. | `src/attune/ops/dismiss_store.py` |
| `load()` | Read the dismiss store. Missing or corrupt file → ``{}``. | `src/attune/ops/dismiss_store.py` |
| `save()` | Persist a dismiss entry for ``slug`` (overwrites prior entry). | `src/attune/ops/dismiss_store.py` |
| `clear()` | Remove the entry for ``slug``. No-op if absent. | `src/attune/ops/dismiss_store.py` |
| `is_active()` | True iff a dismiss for ``slug`` is currently suppressing it. | `src/attune/ops/dismiss_store.py` |
| `compute_allowlist()` | Compute the default + user-supplied Host allowlist. | `src/attune/ops/middleware.py` |
| `settings_path()` | Return the absolute path to the ops settings file. | `src/attune/ops/ops_config_store.py` |
| `load_settings()` | Read persisted ops settings. Missing or corrupt file → ``{}``. | `src/attune/ops/ops_config_store.py` |
| `save_setting()` | Persist a single setting; returns True on success, False on failure. | `src/attune/ops/ops_config_store.py` |
| `resolve_specs_candidates_enabled()` | Resolve the ``specs_candidates_enabled`` setting. | `src/attune/ops/ops_config_store.py` |
| `home()` | — | `src/attune/ops/routes/dashboard.py` |
| `workflows_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `telemetry_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `health_page()` | — | `src/attune/ops/routes/dashboard.py` |
| `sessions_page()` | Sessions page — recent Claude Code sessions for this project. | `src/attune/ops/routes/dashboard.py` |
| `run_view_page()` | Full-page view for one workflow run. | `src/attune/ops/routes/dashboard.py` |
| `specs_page()` | Specs tab — federated listing of all specs across configured roots. | `src/attune/ops/routes/dashboard.py` |
| `spec_detail_page()` | Drill-in for a single spec: show every phase file's content (read-only). | `src/attune/ops/routes/dashboard.py` |
| `start_run()` | — | `src/attune/ops/routes/runner.py` |
| `get_run()` | — | `src/attune/ops/routes/runner.py` |
| `stream_run()` | — | `src/attune/ops/routes/runner.py` |
| `list_runs()` | Return up to 20 newest runs for ``workflow``, newest first. | `src/attune/ops/routes/runs_history.py` |
| `get_run_record()` | Return one persisted run record (metadata + log). | `src/attune/ops/routes/runs_history.py` |
| `enrich_with_summaries()` | Public helper used by both the JSON route and the HTML page. | `src/attune/ops/routes/sessions.py` |
| `list_sessions()` | ``GET /api/sessions`` — JSON listing of recent sessions. | `src/attune/ops/routes/sessions.py` |
| `list_specs()` | Federated listing across all configured spec roots. | `src/attune/ops/routes/specs.py` |
| `list_completion_candidates()` | Return "Ready to close?" candidates for the Specs page. | `src/attune/ops/routes/specs.py` |
| `get_spec()` | Return phase-file contents for one spec. | `src/attune/ops/routes/specs.py` |
| `update_phase_status()` | Rewrite the ``**Status**`` line in the named phase file. | `src/attune/ops/routes/specs.py` |
| `dismiss_completion_candidate()` | Suppress a completion candidate for the default TTL (14 days). | `src/attune/ops/routes/specs.py` |
| `get_sweep_result()` | Return the latest sweep result for a scope-hash, or 404. | `src/attune/ops/routes/sweep_results.py` |
| `get_sweep_chips()` | Return chip counts for an arbitrary scope path. | `src/attune/ops/routes/sweep_results.py` |
| `sweep_detail_page()` | Scope-keyed detail page for the latest discovery-sweep result. | `src/attune/ops/routes/sweep_results.py` |
| `echo_command_builder()` | Test helper: produce a portable subprocess that prints two lines + exits 0. | `src/attune/ops/runner.py` |
| `prune_old_runs()` | Delete persisted run files older than ``days``. Returns the deletion count. | `src/attune/ops/runner.py` |
| `create_app()` | Build the FastAPI app, wiring config + templates into request state. | `src/attune/ops/server.py` |
| `redact()` | Run all redaction passes over ``text`` and return the result. | `src/attune/ops/session_redaction.py` |
| `redact_json_line()` | Redact one JSON-serialized line in-place, preserving structure. | `src/attune/ops/session_redaction.py` |
| `new_budget()` | Build a :class:`Budget` from the env override or default. | `src/attune/ops/session_summarizer.py` |
| `llm_enabled()` | Return True iff the Haiku path is enabled this run. | `src/attune/ops/session_summarizer.py` |
| `summarize_session()` | Return a Haiku-or-cached summary for one session JSONL. | `src/attune/ops/session_summarizer.py` |
| `compute_cache_key()` | Build a :class:`CacheKey` for one JSONL file. ``None`` on I/O failure. | `src/attune/ops/session_summary_cache.py` |
| `cache_path_for()` | Return the on-disk cache path for one session id. | `src/attune/ops/session_summary_cache.py` |
| `load()` | Return the cached summary iff the on-disk record matches ``expected``. | `src/attune/ops/session_summary_cache.py` |
| `save()` | Write a summary to the on-disk cache, atomically. | `src/attune/ops/session_summary_cache.py` |
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
