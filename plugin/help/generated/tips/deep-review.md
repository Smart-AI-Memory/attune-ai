---
name: deep-review
source: content/features/deep-review.md
tags:
- review
- security
- quality
- tests
- comprehensive-review
type: tip
---

# Multi-pass code review across security, quality, and test gaps

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `DeepReviewAgentSDKWorkflow` and its async `execute`, plus the
  `WorkflowResult` it returns. Names with a leading underscore —
  `_run_deep_review`, `_SUBAGENT_DEFS` — are internal and may
  change.
- **Use `focus` to keep runs cheap.** A `focus=["security"]` pass
  is faster and cheaper than the full three-domain review; reserve
  the full `deep` run for pre-merge or release gates.
- **Read `metadata["focus"]` to confirm scope.** It records which
  passes actually ran, which is handy when a caller built the
  focus list dynamically.
- **Start shallow, then deepen.** Run `standard` broadly and spend
  a `deep` run only on the modules that came back risky.
