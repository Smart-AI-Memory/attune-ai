---
type: warning
name: ops-dashboard-warning
feature: ops-dashboard
depth: warning
generated_at: 2026-06-02T10:56:02.723762+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Ops Dashboard Cautions

The ops dashboard runs as a blocking server process (`cmd_ops` returns `0` only after the server exits). The areas below describe the pitfalls most likely to cost you debugging time before you hit them.

## Risk areas

### Stale cost data served as live data

`fetch_summary()` returns a `CostSummary` whose `source` field is either `'live'` or `'cached'`. If you call it without `refresh=True`, you may display cached figures without realizing it. Always check `CostSummary.source` before presenting numbers as current, and use `clear_cache()` only in tests — its docstring marks it as a test-only convenience.

### Missing admin key silently disables cost reporting

`load_admin_key()` returns `None` when the admin API key is unavailable. `fetch_summary()` wraps failures in a `CostFetchError` (fields: `kind`, `message`) rather than raising, so a missing key produces no exception — just a `None` summary alongside a categorized error. If your code unpacks the tuple without inspecting the error half, cost data will silently disappear from the dashboard.

### FastAPI pulled in at import time if `create_app()` is called early

`create_app()` uses a lazy import specifically to avoid pulling FastAPI into the `attune` namespace on import. If you call it at module level — or in a place that runs during `import attune` — you defeat that isolation and add FastAPI to the startup cost of every process that imports the package.

### `Config.allow_run` defaults to `False` and blocks workflow execution

`Config.allow_run` is `False` by default. Workflows will not execute until this is explicitly set to `True`. This is intentional as a safety default, but it is easy to misconfigure when building a `Config` programmatically and then wonder why the runner does nothing.

### `Config.specs_candidates_enabled` gates the candidate detector

`detect_candidates()` scans spec roots only when `Config.specs_candidates_enabled` is `True`. With the default `False`, `detect_candidates()` returns an empty list with no warning. If you expect completion candidates to surface and they do not, check this flag before investigating the detector logic.

### `runs_dir` may not exist until the first write

`Config.runs_dir` documents that the directory "may not exist until first write." Code that reads from `runs_dir` before any run has completed will encounter a missing directory. Guard any read path with an existence check rather than assuming the directory is present after `Config` is constructed.

## How to avoid problems

1. **Always inspect both sides of `fetch_summary()`'s return tuple.** The signature is `tuple[CostSummary | None, CostFetchError | None]`. Treat a non-`None` error as a display-worthy event, not a silent no-op.

2. **Never call `clear_cache()` in production code.** Both the cost module and the candidate detector expose a `clear_cache()` function marked as a test helper. Calling either in production will cause the next request to make a live API call regardless of cache state.

3. **Build `Config` explicitly for non-default behavior.** The safe defaults (`allow_run=False`, `specs_candidates_enabled=False`, `trusted_hosts=()`) mean a programmatically constructed `Config` will silently restrict dashboard capabilities. Pass each field you intend to use rather than relying on defaults.

4. **Depend only on the public API.** The module's `__all__` exports `create_app`, `build_config`, and `Config`. Private helpers (names starting with `_`, such as `_COST_REPORT_URL` and `_API_VERSION`) can change without notice.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
