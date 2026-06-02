---
type: tip
name: deep-review-tip
feature: deep-review
depth: tip
generated_at: 2026-06-02T10:54:11.463750+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Tip: Working effectively with deep review

## Recommendation

Run `deep_review` when you want security, quality, and test-gap findings in a single pass — not as three separate workflow calls.

`DeepReviewAgentSDKWorkflow.execute()` internally coordinates three specialized subagents (`security-reviewer`, `quality-reviewer`, and `test-gap-reviewer`) and synthesizes their output into one consolidated report. Calling each underlying workflow individually loses the cross-domain synthesis step.

## Why

The orchestrator's final synthesis pass — not the subagent findings themselves — is where the prioritized, cross-domain **Suggestions** section is generated. Bypassing it means you never get the top 5–10 actionable next steps ordered by impact.

## Tradeoff

A full deep-review run is slower than a single-domain review because all three subagents complete before synthesis begins. If you only need one dimension (for example, just security), prefer `security-audit` directly rather than filtering deep-review output after the fact.

## Source files

- `src/attune/workflows/deep_review.py`

**Tags:** `review`, `security`, `quality`, `tests`, `comprehensive-review`
