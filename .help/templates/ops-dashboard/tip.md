---
type: tip
name: ops-dashboard-tip
feature: ops-dashboard
depth: tip
generated_at: 2026-06-10T07:07:04.674537+00:00
source_hash: 5a9cf489e3626794b14e2ce54ec4ec47a2ac21cb2d5f13fcb3e0dd6147f0d24f
status: generated
---

# Tip: working effectively with ops dashboard

Use `fetch_summary(refresh=False)` as your entry point for cost data — it handles caching and returns a typed `(CostSummary | None, CostFetchError | None)` tuple so you never have to catch raw HTTP errors yourself.

**Why it sticks:** the cache layer means repeated calls inside a single dashboard render are free; setting `refresh=True` only when you genuinely need live data keeps the Anthropic admin API from rate-limiting you.

**Tradeoff:** the cached value reflects the moment it was last populated, not wall-clock now. Check `CostSummary.fetched_at` and `CostSummary.source` (either `'live'` or `'cached'`) before presenting figures to a user who needs precision.

The three other stable entry points are `create_app()` (the FastAPI factory), `build_config()` (the config builder), and `clear_cache()` — all exported via `__all__` in `src/attune/ops/__init__.py`. Everything else, including anything prefixed with an underscore such as `_COST_REPORT_URL` or `_API_VERSION`, is internal and may change without notice.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
