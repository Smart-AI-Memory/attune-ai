---
type: troubleshooting
name: ops-dashboard-troubleshooting
feature: ops-dashboard
depth: troubleshooting
generated_at: 2026-05-16T06:19:45.808757+00:00
source_hash: 882177b61c372bb6753c706430edfcc0df951fa4fae4106cb76ff02fca34a836
status: generated
---

# Troubleshoot ops dashboard

## Before you start

The ops dashboard is a local FastAPI server (`attune ops` / `python -m attune.ops`) that surfaces workflow execution, per-feature scope picking, persisted run history, and live SSE log streaming. Confirm the server is running before diagnosing anything else:

```bash
attune ops --host 127.0.0.1 --port 8765
```

If the process starts but the browser shows nothing, check that your `Host` header is on the `trusted_hosts` allowlist — `TrustedHostMiddleware` rejects requests whose `Host` header isn't in `Config.trusted_hosts`.

## Symptom table

| If you observe | Check |
|---|---|
| Server refuses to start | Run `python -m attune.ops` directly and read the traceback. The most common cause is a missing or misconfigured `project_root` or `attune_home`. |
| `403` / connection rejected from browser | Confirm your browser's `Host` header matches an entry in `Config.trusted_hosts`. Add your host via `--trusted-hosts` or `build_config(trusted_hosts=(...))`. |
| Dashboard home page shows zero KPIs | Verify `Config.telemetry_path` exists and contains at least one event. The `HomeKpis` fields (`today_cost`, `seven_day_cost`, etc.) are all zero when no telemetry data is present. |
| Workflow list is empty | Confirm `Config.specs_roots` points to directories that contain valid spec files. Pass `--specs-roots` on the CLI or set `specs_roots` in `build_config()`. |
| Scope picker shows no features | Check that `<project_root>/.help/features.yaml` exists and is valid YAML. `list_features()` returns an empty list when the file is missing or unparseable. |
| Run history missing or not persisting | Check that `Config.runs_dir` is writable. The directory is created on first write — if it doesn't exist yet, that is expected until the first run completes. Runs older than `runs_retention_days` (default: 30) are purged automatically. |
| SSE log stream drops or never connects | Confirm nothing between the browser and the server (proxy, firewall) is buffering the response. SSE requires a persistent HTTP connection with chunked transfer. |
| `allow_run` errors / workflow won't execute | `Config.allow_run` defaults to `False`. Pass `--allow-run` on the CLI or set `allow_run=True` in `build_config()`. |

## Diagnosis steps

Work through these in order — each step is cheaper than the next.

1. **Reproduce with the standalone entrypoint.**
   Run `python -m attune.ops` with the same arguments you use in production. This isolates the failure from any wrapper script or environment the `attune` CLI adds.

2. **Confirm `Config` values at startup.**
   `build_config()` assembles every runtime value. Add a temporary print or log statement immediately after calling it to confirm `project_root`, `attune_home`, `host`, `port`, `specs_roots`, `trusted_hosts`, and `allow_run` all have the values you expect. Environment overrides (such as `ATTUNE_HOME`) silently take precedence over defaults.

3. **Check the telemetry file directly.**
   `Config.telemetry_path` resolves to a file under `attune_home`. If KPIs are wrong, open that file and verify it contains recent, well-formed events. An empty or corrupt file produces zero-value `TelemetrySummary` fields without raising an error.

4. **Check the runs directory.**
   `Config.runs_dir` may not exist until the first run completes. If you expect historical runs and the directory is absent or empty, either no runs have completed or `runs_retention_days` has purged them. Confirm with:
   ```bash
   ls -la "$(python -c "import attune.ops as o; print(o.build_config().runs_dir)")"
   ```

5. **Run the related tests.**
   ```bash
   pytest -k "ops" -v
   ```
   A failing test in this suite narrows the fault to a specific code path and gives you a reproducible fixture to work from.

6. **Enable FastAPI/uvicorn debug logging.**
   Set the log level before starting the server:
   ```bash
   UVICORN_LOG_LEVEL=debug attune ops
   ```
   Request-level logs will show whether `TrustedHostMiddleware` is rejecting connections and where routing fails.

## Common fixes

**Server won't start — `project_root` or `attune_home` not found**
Pass explicit paths:
```bash
attune ops --project-root /path/to/project
```
Or set the environment variable that `attune_home()` reads:
```bash
export ATTUNE_HOME=/path/to/.attune
attune ops
```

**Scope picker empty — missing `features.yaml`**
Create the file at `<project_root>/.help/features.yaml`. `list_features()` requires this file to exist and be valid YAML. `first_feature()` returns `None` when it is absent, leaving the scope picker blank.

**Workflows not running — `allow_run` is `False`**
```bash
attune ops --allow-run
```
This sets `Config.allow_run = True`. Note that this change affects the entire dashboard session; there is no per-workflow override.

**Stale runs cluttering history — retention too long**
Lower the retention window:
```bash
attune ops --runs-retention-days 7
```
Runs older than the specified number of days are purged automatically on the next startup.

**Dependency version mismatch — FastAPI or uvicorn behaves unexpectedly**
`create_app()` lazy-imports FastAPI to avoid pulling it into every `attune` import. If FastAPI behaviour changed after an upgrade, confirm the installed version:
```bash
pip show fastapi uvicorn
```
Pin to a known-good version in your project's requirements if needed. This is a change outside `ops-dashboard` itself.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
