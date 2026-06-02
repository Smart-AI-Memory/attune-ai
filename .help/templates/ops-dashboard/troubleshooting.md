---
type: troubleshooting
name: ops-dashboard-troubleshooting
feature: ops-dashboard
depth: troubleshooting
generated_at: 2026-06-02T10:56:02.727078+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Troubleshoot ops dashboard

The ops dashboard is the `attune ops` operations interface — a workflow runner with a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. It runs as a local server (default `127.0.0.1:8765`) and is started via `python -m attune.ops` or the `attune ops` CLI subcommand.

## Symptom table

| If you observe | Check |
|---|---|
| Dashboard server fails to start | Confirm `host` and `port` in your `Config` are not already bound. The default is `127.0.0.1:8765`. Run `lsof -i :8765` to check for a port conflict. |
| Cost data is missing or stale | Check whether `load_admin_key()` returns `None` — this means `ANTHROPIC_ADMIN_KEY` (or equivalent) is unset or unreadable. Also inspect the `source` field on `CostSummary`: `'cached'` means the live fetch was skipped. Call `fetch_summary(refresh=True)` to force a new fetch. |
| `fetch_summary()` returns a `CostFetchError` | Read `CostFetchError.kind` and `CostFetchError.message`. The `kind` field is a `CostFetchErrorKind` enum that categorises the failure (network, auth, parse, etc.). |
| Spec completion candidates not appearing | Verify `specs_candidates_enabled = True` in `Config` and that `specs_roots` contains at least one valid path. Run `detect_candidates(config)` directly to see what the detector finds. |
| Run history is empty or not persisted | Check that `Config.runs_dir` exists on disk — it is not created until the first write. Verify `runs_retention_days` is not set to `0`. |
| Sessions page shows no sessions | Confirm `Config.sessions_dir` exists and contains session files. The `Session.source` field will be `'heuristic'` for auto-detected sessions. |
| Scope picker shows no features | Check that `.help/features.yaml` exists under your project root and that each entry has a valid `name` and `path`. |
| Dashboard refuses a cross-origin request | Add the calling host to `Config.trusted_hosts`. |

## Diagnosis steps

Work through these in order — each step is cheaper than the one that follows it.

1. **Reproduce the failure with the minimal invocation.**
   Run `python -m attune.ops` directly (or `attune ops`) and observe the exact error or misbehaviour. Strip away any wrapper scripts so you're working with the raw entry point.

2. **Check `Config` values before the server starts.**
   Call `build_config()` and print the resulting `Config` dataclass. Confirm `project_root`, `attune_home`, `host`, `port`, `specs_roots`, and `allow_run` match your expectations. Many startup failures trace back to a wrong path or a flag left at its default.

3. **Check the admin key for cost features.**
   Call `load_admin_key()`. If it returns `None`, cost reporting will fail silently — no exception is raised at startup. Set the key in your environment before starting the server.

4. **Force a cache refresh for cost data.**
   Call `fetch_summary(refresh=True)`. Inspect the returned `CostFetchError` if the first element of the tuple is `None` — `CostFetchError.kind` and `CostFetchError.message` together identify whether the problem is network, authentication, or response parsing. To reset the in-memory cache entirely, call `clear_cache()`.

5. **Run the related tests.**
   ```
   pytest -k "ops" -v
   ```
   If a test covers the failing path, its fixtures give you a reproducible starting point and confirm whether the issue is in your environment or the code itself.

6. **Inspect `telemetry_path` for accumulated state.**
   If behaviour is correct on a clean run but wrong after repeated use, check the telemetry file at `Config.telemetry_path`. Stale telemetry or a corrupted `spec_completion_dismissed.json` (stored under `ops/` inside `attune_home`) can cause the dashboard to behave inconsistently.

## Common fixes

**Port already in use**
```
lsof -i :8765
kill -9 <PID>
```
Or set a different port by passing `--port <N>` to `attune ops`, which maps to `Config.port`.

**Admin key not found — cost panel blank**
Export the key before starting the server:
```
export ANTHROPIC_ADMIN_KEY="sk-admin-..."
python -m attune.ops
```
`load_admin_key()` reads this at runtime; restarting the server after exporting is required.

**Stale cost cache**
Call `clear_cache()` (defined in `attune.ops.anthropic_cost`) then call `fetch_summary(refresh=True)`. Note that `clear_cache()` is documented as a test helper — in production, prefer `fetch_summary(refresh=True)`.

**Spec candidates not detected**
Set `specs_candidates_enabled = True` in your config and populate `specs_roots` with the directories that contain your spec files. Then verify with:
```python
from attune.ops import build_config
from attune.ops.specs_candidates import detect_candidates
config = build_config()
print(detect_candidates(config))
```
Each returned `Candidate` has a `slug`, `path`, `current_status`, and `evidence` list you can inspect.

**Run history not persisting**
`Config.runs_dir` is not created on startup — it is created on first write. If you see no history, check whether any run has ever completed successfully and written to that directory. If the directory exists but is empty, check `runs_retention_days`; runs older than that value are pruned.

**FastAPI not installed**
`create_app()` uses a lazy import to avoid pulling FastAPI when you import `attune`. If the dashboard fails to start with an `ImportError`, install the server dependencies:
```
pip install "attune[ops]"
```
Then confirm with `pip show fastapi`.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 75 (code fence) | error | `from attune.ops.specs_candidates import …` — module not importable |
