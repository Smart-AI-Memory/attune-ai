---
name: code-quality
source: content/features/code-quality.md
tags:
- review
- quality
- bugs
- lint
type: tip
---

# Multi-subagent code review across security, quality, performance, and architecture

## Notes & tips

- **Depend on the documented public surface.** The supported API is
  `CodeReviewWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_agent_review`, `_SUBAGENT_NAMES` — are internal and may
  change.
- **Use `path` and `depth` to keep runs cheap.** A `quick` pass
  over one subsystem is far faster than a `deep` pass over `src/`;
  reserve the full `deep` run for pre-merge or release gates.
- **Watch for the bug-predict recommendation.** When the review
  surfaces security-shaped findings, the run emits an `ATTUNE_REC`
  suggesting a `bug-predict` pass on the same scope to locate the
  exact lines.
- **Read `metadata` to confirm scope.** It records the `path`,
  `depth`, and `max_turns` the run actually used.
