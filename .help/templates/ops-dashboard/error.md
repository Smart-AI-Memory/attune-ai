---
type: error
name: ops-dashboard-error
feature: ops-dashboard
depth: error
generated_at: 2026-06-02T10:56:02.715960+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Ops Dashboard errors

## Common error signatures

Most failures in the ops dashboard fall into one of two categories: cost-report fetch failures and configuration or startup failures.

**Cost-report fetch failures** are represented by `CostFetchError`, a categorized error dataclass returned (never raised) by `fetch_summary()`. Its `kind` field contains a `CostFetchErrorKind` value and its `message` field contains a human-readable description. Common causes include:

- No admin API key available — `load_admin_key()` returns `None`, so `fetch_summary()` cannot authenticate against `https://api.anthropic.com/v1/organizations/cost_report`.
- A non-success HTTP response or network-level failure reaching the cost-report endpoint.
- A stale or unparseable cached response when `refresh=False`.

**Configuration and startup failures** occur before the dashboard server is running:

- `build_config()` fails when required paths (`project_root`, `attune_home`) cannot be resolved.
- `create_app()` raises an `ImportError`-family exception if FastAPI is not installed; the lazy-import design means this only surfaces at call time, not at `import attune`.
- `cmd_ops()` exits non-zero (returns a value other than `0`) when the server cannot bind to `Config.host`/`Config.port` (default `127.0.0.1:8765`).

## How to diagnose

1. **Check whether `fetch_summary()` returned an error.** The function signature is `fetch_summary(*, refresh: bool = False) -> tuple[CostSummary | None, CostFetchError | None]`. If the second element of the tuple is not `None`, inspect `CostFetchError.kind` for the error category and `CostFetchError.message` for the detail. A non-`None` error with a `None` summary means no cost data is available.

2. **Verify the admin API key is present.** Call `load_admin_key()` directly. If it returns `None`, the dashboard cannot reach the Anthropic cost-report API and every `fetch_summary()` call will produce a `CostFetchError`.

3. **Confirm FastAPI is installed before calling `create_app()`.** Because the import is deferred, an `ImportError` will not appear until `create_app()` is called. If you see an `ImportError` or `ModuleNotFoundError` mentioning FastAPI at that point, install the ops extras.

4. **Check the configured host and port.** If `cmd_ops()` returns a non-zero exit code immediately, the server likely failed to bind. Inspect the `Config` values for `host` (default `127.0.0.1`) and `port` (default `8765`) and confirm nothing else is listening on that address.

5. **Review `Config.specs_roots` when `detect_candidates()` returns nothing.** The `specs_candidates_enabled` field must be `True` and `specs_roots` must contain at least one valid `Path` for candidate detection to run. An empty tuple for `specs_roots` is a silent no-op, not an exception.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
