---
name: bug-predict
source: content/features/bug-predict.md
tags:
- bugs
- prediction
- scanning
- race-condition
type: tip
---

# Predict likely bug hotspots with three Agent SDK subagents

## Notes & tips

- **Depend on the documented public surface.** The supported API
  is `BugPredictionWorkflow` (its constructor and async
  `execute`) plus the `WorkflowResult` it returns. Names with a
  leading underscore — the pattern helpers in
  `bug_predict_patterns.py` and `_run_agent_predict` — are
  internal and may change.
- **`format_bug_predict_report` and `main` were removed.** They
  consumed the pre-v4.2.0 dict pipeline shape
  (`overall_risk_score`, `patterns_found`, …), not the
  `WorkflowResult` that `execute` returns, and had no live caller
  once the SDK-native rewrite shipped. Read `result.final_output`
  (a `WorkflowReport` when subagent findings parsed as structured
  output, rendered via `attune.voice.report_renderer.render()`)
  and `result.summary` directly instead.
- **Start shallow, then deepen.** Run `quick` to triage, and only
  spend a `deep` budget on the modules that came back hot.
- **Use `--cheap` for routine CLI runs.** It forces unpinned
  subagents onto Haiku, trading some depth for cost.
