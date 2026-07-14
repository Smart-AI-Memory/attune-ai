---
type: tip
name: bug-predict-tip
feature: bug-predict
depth: tip
generated_at: 2026-07-14T22:05:25.786099+00:00
source_hash: 6651bf938b845a590d6af44512242264ef0650223553d1e58325a8c0c6b2e208
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
