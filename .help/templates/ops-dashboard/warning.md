---
type: warning
name: ops-dashboard-warning
feature: ops-dashboard
depth: warning
generated_at: 2026-06-10T07:07:04.664173+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Ops Dashboard Cautions

The ops dashboard runs a local FastAPI server (`python -m attune.ops`) that combines a workflow runner, a per-feature scope picker, persisted run history, and live SSE log streaming. Most surprises come from three areas: the in-memory cost cache, the admin API key lookup, and configuration fields that silently restrict what the server allows.

## Risk areas

### `fetch_summary()` returns stale data by default

`fetch_summary(*, refresh: bool = False)` returns a cached `CostSummary` when `refresh` is `False`. If you call it without setting `refresh=True`, the `source` field on the returned `CostSummary` will be `'cached'`, and the cost figures (`today_usd`, `seven_day_usd`, `month_to_date_usd`, `thirty_day_usd`) will reflect whenever the cache was last populated — not the current moment. Always check `CostSummary.source` before presenting figures as live, and pass `refresh=True` when you need a current snapshot.

### `load_admin_key()` returns `None` silently

`load_admin_key()` returns `None` if the admin API key is unavailable rather than raising an exception. Code that passes the result directly to an HTTP client will fail later with a confusing auth error instead of a clear "key not configured" message. Check for `None` before use and surface a clear error to the user at that point.

### `clear_cache()` is a test helper, not a lifecycle hook

`clear_cache()` in `attune.ops.anthropic_cost` is documented as a test-only convenience. Calling it in production code to force a refresh will work, but it bypasses the `refresh` parameter contract of `fetch_summary()` and can cause cache stampedes if multiple requests arrive simultaneously. Use `fetch_summary(refresh=True)` instead.

### `Config.allow_run` gates workflow execution

`Config.allow_run` defaults to `False`. With that default, the dashboard will load and display workflows but silently refuse to execute them. If you deploy the dashboard and find that run buttons have no effect, check this field first. Set it to `True` only in environments where you intend to allow workflow execution.

### `Config.trusted_hosts` controls which origins the server accepts

`Config.trusted_hosts` defaults to an empty tuple. Requests from hosts not in this tuple will be rejected. When running the dashboard behind a proxy or in a non-localhost environment, add the proxy's hostname to `trusted_hosts` before starting the server — otherwise every request will fail and the error will appear to come from the network layer, not from configuration.

### `create_app()` and `build_config()` defer their imports

Both functions use lazy imports to avoid pulling FastAPI into the `attune` namespace at import time. If FastAPI is missing from the environment, the failure surfaces only when you first call one of these functions, not at `import attune`. If the server fails to start unexpectedly, verify FastAPI is installed before looking elsewhere.

## How to avoid problems

1. **Check `CostSummary.source` after every `fetch_summary()` call.** A value of `'cached'` means the figures may be hours old. Pass `refresh=True` when you need current data.

2. **Guard against `None` from `load_admin_key()`.** Treat a `None` return as a configuration error and fail fast with a descriptive message rather than propagating `None` into downstream calls.

3. **Set `allow_run` and `trusted_hosts` explicitly in production configs.** Both fields have defaults that are safe for local development but will cause silent failures in other environments.

4. **Use `fetch_summary(refresh=True)` instead of `clear_cache()`.** Reserve `clear_cache()` for test setup and teardown only.

5. **Depend only on the public API.** `__all__` exports `create_app`, `build_config`, and `Config`. Functions and constants prefixed with `_` (such as `_COST_REPORT_URL` and `_API_VERSION`) can change without notice.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
