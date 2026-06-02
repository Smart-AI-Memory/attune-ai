---
type: tip
name: ops-dashboard-tip
feature: ops-dashboard
depth: tip
generated_at: 2026-06-02T10:56:02.737540+00:00
source_hash: 78a1505f787430bd8780c3c1f1998c5f2effda3f2c6da5faea59340e02c22f53
status: generated
---

# Tip: working effectively with ops dashboard

Use `fetch_summary(refresh=True)` when you need a live cost reading instead of relying on the cached result — the `source` field on `CostSummary` tells you whether you got `'live'` or `'cached'` data, so you can always verify what you received.

**Why:** `fetch_summary` returns a `(CostSummary | None, CostFetchError | None)` tuple, and silent cache hits are the most common reason cost figures look stale.

**Tradeoff:** Passing `refresh=True` on every call adds a network round-trip to `https://api.anthropic.com/v1/organizations/cost_report` and requires a valid key from `load_admin_key()`. If the key is unavailable, `fetch_summary` returns `None` for the summary and a populated `CostFetchError` — check `CostFetchError.kind` and `CostFetchError.message` before assuming the data is valid.

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
