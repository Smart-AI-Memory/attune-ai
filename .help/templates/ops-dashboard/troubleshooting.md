---
type: troubleshooting
name: ops-dashboard-troubleshooting
feature: ops-dashboard
depth: troubleshooting
generated_at: 2026-06-10T07:07:04.666526+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Troubleshoot ops dashboard

## Before you start

The ops dashboard (`attune ops` / `python -m attune.ops`) is a local FastAPI server that provides a workflow runner with a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. It binds to `127.0.0.1:8765` by default and reads project state from the paths defined in `Config`.

## Symptom table

| If you observe | Check |
|---|---|
| Dashboard server won't start | Confirm no other process is using port `8765` (or your configured `Config.port`). Check that `Config.project_root` and `Config.attune_home` resolve to real directories. |
| Cost data missing or stale | Call `fetch_summary(refresh=True)` to bypass the in-memory cache. Check that `load_admin_key()` returns a non-`None` value — if it returns `None`, the Anthropic admin key is absent or unreadable. |
| `CostFetchError` returned instead of `CostSummary` | Inspect the `CostFetchError.kind` and `CostFetchError.message` fields. The `kind` field narrows the failure to a specific `CostFetchErrorKind` category (auth, network, parsing, etc.). |
| `CostSummary.source` is `'cached'` when you expect live data | Call `clear_cache()` then re-request. This empties the in-memory cache and forces a fresh fetch on the next call to `fetch_summary()`. |
| Spec completion candidates not appearing | Verify `Config.specs_candidates_enabled` is `True` and that `Config.specs_roots` is non-empty. Run `detect_candidates(config)` directly and inspect the returned `list[Candidate]`. |
| Sessions page is empty | Check that `Config.sessions_dir` exists on disk. The directory is under `Config.attune_home` and may not be created until the first session write. |
| Run history missing | Check that `Config.runs_dir` exists. Like `sessions_dir`, it is only created on the first write. Confirm `Config.runs_retention_days` (default `30`) has not expired old entries. |
| `cmd_ops` exits immediately with a non-zero code | Check the return value and any stderr output. `cmd_ops` returns `0` on clean exit; any other value indicates a startup failure. |

## Diagnosis steps

1. **Reproduce the failure with the minimal invocation.**
   Run `python -m attune.ops` (or `attune ops`) in your project root with no extra flags. If the failure disappears, a CLI flag or environment variable in your normal invocation is the cause.

2. **Confirm the admin API key is present.**
   Call `load_admin_key()` in a Python REPL. If it returns `None`, the dashboard cannot reach the Anthropic cost-report endpoint at `https://api.anthropic.com/v1/organizations/cost_report`. Set the key in your environment before proceeding.

3. **Check the cache before deeper investigation.**
   Call `clear_cache()` and retry the failing operation. Cost-fetch failures and stale data are often explained by a poisoned in-memory cache, and clearing it takes seconds.

4. **Inspect `Config` field values.**
   Build a config with `build_config()` and print the relevant fields (`project_root`, `attune_home`, `host`, `port`, `specs_roots`, `specs_candidates_enabled`). Mismatched paths are a common root cause for missing data and silent failures.

5. **Call `fetch_summary` directly and examine the error.**
   ```python
   summary, error = fetch_summary(refresh=True)
   if error:
       print(error.kind, error.message)
   ```
   The `CostFetchError.kind` field tells you whether the failure is an auth error, a network error, or a parsing error — each has a different fix.

6. **Run `detect_candidates` directly for spec-completion issues.**
   ```python
   from attune.ops import build_config
   from attune.ops.specs_candidates import detect_candidates
   config = build_config()
   candidates = detect_candidates(config)
   ```
   If the list is empty, check `config.specs_roots` and `config.specs_candidates_enabled`.

7. **Run the related tests.**
   ```
   pytest -k "ops" -v
   ```
   A failing test that exercises your symptom confirms the regression and provides a fixture you can adapt for further isolation.

## Common fixes

- **Admin key not loaded — cost data unavailable.**
  `load_admin_key()` reads the key from your environment. Export the key before starting the server:
  ```bash
  export ANTHROPIC_ADMIN_KEY="sk-admin-..."
  attune ops
  ```

- **Stale cost data.**
  Force a cache reset without restarting the server:
  ```python
  from attune.ops.anthropic_cost import clear_cache
  clear_cache()
  ```
  The next call to `fetch_summary()` will hit the live endpoint.

- **Port already in use.**
  Change the port in your `Config` (field: `port`) or free the existing listener:
  ```bash
  lsof -i :8765        # find the PID
  kill <PID>
  attune ops
  ```

- **Missing runs or sessions directory.**
  `Config.runs_dir` and `Config.sessions_dir` are created on first write, not on startup. If you need them to exist before the first run (for example, in a CI setup), create them manually:
  ```bash
  mkdir -p "$(python -c 'from attune.ops import build_config; print(build_config().runs_dir)')"
  ```

- **Spec candidates disabled or no roots configured.**
  In your config source, set `specs_candidates_enabled = True` and populate `specs_roots` with at least one valid path. This change is in your project's config, outside the dashboard itself.

- **Dependency version drift.**
  A FastAPI or Anthropic SDK upgrade can silently change behavior. Check installed versions:
  ```bash
  pip show fastapi anthropic
  ```
  Pin to the versions your project targets if the output differs from expectations.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
