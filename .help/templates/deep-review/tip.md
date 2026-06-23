---
type: tip
name: deep-review-tip
feature: deep-review
depth: tip
generated_at: 2026-06-23T15:11:33.648986+00:00
source_hash: 5e2ccde04cab83b41196f2c5f05ef11b8e7be00e39bb8040b02fb2a225aef083
status: generated
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
