---
type: note
name: ops-dashboard-note
feature: ops-dashboard
depth: note
generated_at: 2026-06-02T10:56:02.739815+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Note: ops dashboard

## Context

`attune ops` is a local operations dashboard for the workflow OS. You can start it directly with `python -m attune.ops` or through the `attune ops` CLI subcommand (registered by `add_subparser`). The server binds to `127.0.0.1:8765` by default and runs blocking until stopped.

The dashboard provides a per-feature scope picker, persisted run history, clickable workflow chaining, and live SSE log streaming. All state roots — runs, sessions, memory, bulletins — are derived from `Config`, which exposes them as computed properties (`runs_dir`, `sessions_dir`, `memory_dir`, `bulletin_dir`, `telemetry_path`).

## Public surface

`attune.ops` exports three names at the package boundary: `create_app`, `build_config`, and `Config`. Both `create_app` and `build_config` use lazy imports so that importing `attune` does not pull in FastAPI as a dependency.

The remaining public classes and functions live one level deeper:

| Name | Location | Role |
|---|---|---|
| `CostSummary` | `src/attune/ops/anthropic_cost.py` | Account-level cost data from the Anthropic admin cost-report API (`/v1/organizations/cost_report`). Carries today, 7-day, month-to-date, and 30-day totals plus per-day, per-model, and per-cost-type breakdowns. |
| `CostFetchError` | `src/attune/ops/anthropic_cost.py` | Categorized failure returned alongside `None` when `fetch_summary()` cannot reach or parse the cost report. |
| `Candidate` | `src/attune/ops/completion_candidates.py` | One spec identified by `detect_candidates()` as a completion candidate. |
| `Config` | `src/attune/ops/config.py` | Single source of truth for project root, attune home, server host/port, spec roots, trusted hosts, and retention policy. |
| `fetch_summary()` | `src/attune/ops/anthropic_cost.py` | Returns `(CostSummary, None)` on success or `(None, CostFetchError)` on failure. Accepts a `refresh` flag to bypass the in-memory cache. |
| `detect_candidates()` | `src/attune/ops/completion_candidates.py` | Scans all paths in `Config.specs_roots` and returns every spec that qualifies as a completion candidate. Only active when `Config.specs_candidates_enabled` is `True`. |

## Design notes

- **Cost report caching.** `fetch_summary()` caches results in memory. `clear_cache()` resets the cache and is intended for tests only.
- **Admin key.** `load_admin_key()` returns the Anthropic admin API key or `None` if it is unavailable. `fetch_summary()` calls this internally; a missing key produces a `CostFetchError`.
- **Run retention.** Persisted ops runs older than `Config.runs_retention_days` (default 30) are eligible for cleanup. The `runs_dir` property on `Config` points to the disk root; the directory may not exist until the first write.
- **Spec candidates.** Candidate detection is opt-in via `Config.specs_candidates_enabled`. When enabled, `detect_candidates()` cross-references `_PR_REF_FILES` (`decisions.md`, `tasks.md`) against the configured spec roots.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
