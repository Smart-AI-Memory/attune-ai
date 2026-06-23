---
type: tip
name: bug-predict-tip
feature: bug-predict
depth: tip
generated_at: 2026-06-23T12:37:44.972124+00:00
source_hash: 3c6441a981e2df351b5043ad522cb27f0fed3c7907db1157a7f65632cc74504d
status: generated
---

# Predict likely bug hotspots with three Agent SDK subagents

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `BugPredictionWorkflow` (its constructor and async
  `execute`) plus the `WorkflowResult` it returns. Names with a
  leading underscore — the pattern helpers in
  `bug_predict_patterns.py` and `_run_agent_predict` — are
  internal and may change.
- **`format_bug_predict_report` and `main` are legacy.**
  `format_bug_predict_report(result, input_data)` consumes the
  pre-v4.2.0 dict pipeline shape (`overall_risk_score`,
  `patterns_found`, …), not the `WorkflowResult` that `execute`
  returns; do not feed it `execute`'s output. Read
  `result.final_output` and `result.summary` directly instead.
- **Start shallow, then deepen.** Run `quick` to triage, and only
  spend a `deep` budget on the modules that came back hot.
- **Use `--cheap` for routine CLI runs.** It forces unpinned
  subagents onto Haiku, trading some depth for cost.
