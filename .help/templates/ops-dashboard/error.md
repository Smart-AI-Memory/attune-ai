---
type: error
name: ops-dashboard-error
feature: ops-dashboard
depth: error
generated_at: 2026-06-10T07:07:04.658159+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Ops Dashboard errors

## Common error signatures

Most failures in the ops dashboard fall into one of two categories: cost-report fetch errors and configuration errors.

**Cost-report fetch errors** are represented by `CostFetchError`, a dataclass with two fields:

- `kind: CostFetchErrorKind` — a categorized enum value identifying what went wrong (for example, a missing admin key, a network failure, or an unexpected API response)
- `message: str` — a human-readable description of the failure

`fetch_summary()` always returns a `(CostSummary | None, CostFetchError | None)` tuple. When the second element is not `None`, the fetch failed and the first element is `None`. A `CostSummary` with `source='cached'` means the live fetch failed silently and an older result was served instead — check the `fetched_at` field to assess staleness.

**Configuration errors** surface when `build_config()` cannot construct a valid `Config`. Missing or inaccessible paths for `project_root` or `attune_home` are the most common cause.

## Where errors originate

- `fetch_summary(*, refresh: bool = False)` — Returns `(None, CostFetchError)` when the Anthropic admin cost-report endpoint at `https://api.anthropic.com/v1/organizations/cost_report` is unreachable, returns a non-success status, or when `load_admin_key()` returns `None`.
- `load_admin_key()` — Returns `None` rather than raising when the admin API key is absent. A `None` result here is the most common upstream cause of a failed `fetch_summary()` call.
- `build_config()` — Raises during startup if the resolved `Config` fields (such as `project_root` or `attune_home`) refer to paths the process cannot access.
- `create_app()` — Defers the FastAPI import until call time; an `ImportError` here means FastAPI is not installed in the current environment.

## How to diagnose

1. **Check whether `fetch_summary()` returned a `CostFetchError`.** Inspect the `kind` and `message` fields directly — they identify the failure category without requiring a stack trace.

2. **Verify the admin key is available.** Call `load_admin_key()` in isolation. If it returns `None`, the dashboard cannot reach the cost-report API regardless of network state. Ensure the key is present in the expected environment variable or credentials file before investigating further.

3. **Confirm `CostSummary.source`.** If the dashboard is displaying cost data but the figures look stale, check whether `source == 'cached'`. Compare `fetched_at` against the current time to determine how old the cached result is, then investigate why the live fetch failed.

4. **Reproduce the `build_config()` failure path.** If the dashboard fails to start, run `python -m attune.ops` directly. A startup error will print the exception and the `Config` field that could not be resolved, making it straightforward to identify which path is missing or inaccessible.

5. **Check for a missing FastAPI installation.** If `create_app()` raises `ImportError`, FastAPI is not installed. The lazy-import design means this error only appears at server startup, not at import time.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
