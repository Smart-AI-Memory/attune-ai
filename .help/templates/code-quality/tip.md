---
type: tip
feature: code-quality
depth: tip
generated_at: 2026-04-14T14:41:47.848331+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Use CodeReviewWorkflow for comprehensive code analysis

Use `CodeReviewWorkflow` when you need thorough code review coverage across multiple domains. This workflow coordinates four specialized subagents (security, quality, performance, and architecture reviewers) to produce a unified report with scored findings and prioritized suggestions.

The workflow eliminates the guesswork of manual review sequencing and ensures consistent coverage across all critical code health dimensions.

**Tradeoff:** The comprehensive analysis takes longer than single-domain tools, so use targeted reviewers for quick iterations and `CodeReviewWorkflow` for milestone reviews or merge gates.
