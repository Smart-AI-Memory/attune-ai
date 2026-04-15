---
type: tip
feature: deep-review
depth: tip
generated_at: 2026-04-14T14:55:18.418450+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Tip: working effectively with deep review

Run deep reviews on complete feature branches, not individual commits.

The multi-pass workflow coordinates three specialized subagents (security, quality, and test gaps) that need to see the full context of your changes to provide meaningful analysis. Running reviews on partial code or single files produces fragmented findings that miss cross-cutting concerns.

The tradeoff is longer execution time, but you get a consolidated report with severity rankings and actionable next steps rather than disconnected observations.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`
