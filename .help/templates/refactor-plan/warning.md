---
type: warning
name: refactor-plan-warning
feature: refactor-plan
depth: warning
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Refactor Plan cautions

## What to watch for

A refactor plan roadmap is only as reliable as the analysis that produced it. Three subagents — `debt-scanner`, `impact-analyzer`, and `plan-generator` — each contribute findings that `RefactorPlanWorkflow.execute()` synthesizes into a single report. If the path you supply is incomplete, or if one subagent's output is sparse, the synthesized roadmap can quietly under-report issues without raising an error.

## Risk areas

### Partial-path analysis produces a misleadingly clean score

`RefactorPlanWorkflow.execute()` scans whatever path you give it and scores only what it finds. Pointing the workflow at a subdirectory rather than the full module boundary means coupling issues and cross-file duplication that cross that boundary will be missed. The resulting tech debt score (0–100) will appear better than it is. Always align the analysis path with a meaningful module or package boundary, not a convenience slice of the tree.

### `format_refactor_plan_report()` silently accepts empty input

`format_refactor_plan_report(result, input_data)` formats whatever you pass it. If `result` is an empty dict — for example, because `execute()` returned a `WorkflowResult` whose payload was not unpacked before being passed — the function returns a structurally valid but content-free report rather than raising an error. Verify that `result` contains the expected `Summary`, `Refactoring`, and `Suggestions` sections before passing it to the formatter.

### Effort and risk estimates are model-generated, not measured

The roadmap's effort estimates (`small` / `medium` / `large`) and risk levels (`low` / `medium` / `high`) come from the `plan-generator` subagent's interpretation of the other subagents' findings, not from static analysis metrics. A `Risk: Low` label on a rename in a widely-imported module does not account for callers outside the scanned path. Treat these labels as a starting point for planning, not a substitute for your own impact assessment.

### Private subagent names can change without notice

The subagent identifiers `debt-scanner`, `impact-analyzer`, and `plan-generator` are internal constants. If you have tooling or logging that keys on these names, it will break silently if the constants change. Depend on the public `RefactorPlanWorkflow` and `format_refactor_plan_report` surface instead.

## How to avoid problems

1. **Set the path at a real module boundary.** Run `/refactor-plan src/auth/` rather than `/refactor-plan src/auth/utils/` so that cross-file coupling and duplication are fully visible to all three subagents.

2. **Validate `WorkflowResult` before formatting.** Unpack and inspect the result of `execute()` before passing it to `format_refactor_plan_report()`. Confirm the dict contains substantive content; an empty or minimal result is a signal to re-run, not to format and act on.

3. **Generate tests before acting on high-risk items.** For any roadmap item marked `Risk: High`, ask for a test suite covering the target file before making structural changes. This is especially important for items flagged as god classes or high-complexity functions, where the refactoring surface is large.

4. **Depend only on the public API.** Build any automation around `RefactorPlanWorkflow` and `format_refactor_plan_report` — both in `workflows.refactor_plan` and `workflows.refactor_plan_report`. Avoid referencing internal constants by name.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
