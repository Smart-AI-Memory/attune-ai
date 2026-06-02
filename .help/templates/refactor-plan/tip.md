---
type: tip
name: refactor-plan-tip
feature: refactor-plan
depth: tip
generated_at: 2026-06-02T10:56:02.705686+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Tip: Use `format_refactor_plan_report()` to read results outside the conversation

## Recommendation

When you need the refactor-plan output in a script or CI pipeline, call
`format_refactor_plan_report(result, input_data)` from
`workflows.refactor_plan_report` directly. It converts the raw `WorkflowResult`
dict into a human-readable report with the same Summary, Refactoring, and
Suggestions sections you see in a Claude Code conversation.

**Why:** The three internal subagents (`debt-scanner`, `impact-analyzer`,
`plan-generator`) are underscore-prefixed internals that can change without
notice. `format_refactor_plan_report()` is the stable surface for consuming
their synthesized output.

**Tradeoff:** The function expects the result dict that `RefactorPlanWorkflow.execute()`
produces. If you pass a partial or hand-constructed dict, sections may render
incomplete. Run `execute()` first; don't shortcut by constructing the dict
yourself.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
