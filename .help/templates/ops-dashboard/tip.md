---
type: tip
name: ops-dashboard-tip
feature: ops-dashboard
depth: tip
generated_at: 2026-05-14T14:43:23.573744+00:00
source_hash: 395f221f9a789d9b8851955c90a8bcc4904e7c84a247bacee7036e1583b0ea42
status: generated
---

# Tip: Working effectively with ops-dashboard

Set `allow_run: bool = False` explicitly in your `Config` when you start the dashboard — don't rely on the default.

**Why:** The `allow_run` field gates whether the dashboard can trigger workflow runs. Leaving it at its default (`False`) in production prevents the dashboard from executing workflows unintentionally, but forgetting to set it to `True` in a development environment will silently block all run attempts with no obvious error.

**Tradeoff:** Hardcoding `allow_run=True` in a shared config makes your development setup convenient but increases the risk of accidentally running workflows against production data if that config leaks. Pass it as a `build_config()` argument instead of baking it into a committed file.

## Source files

- `src/attune/ops/**`

**Tags:** `ops`, `dashboard`, `runner`, `workflows`, `scope-picker`, `persistence`, `sse`
