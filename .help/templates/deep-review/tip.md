---
type: tip
name: deep-review-tip
feature: deep-review
depth: tip
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 0166eb83fb8436c203cdd073439a7339645f40e53cdfe39db4fbed0559eac81d
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
