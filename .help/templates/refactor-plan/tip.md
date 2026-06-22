---
type: tip
name: refactor-plan-tip
feature: refactor-plan
depth: tip
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
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
