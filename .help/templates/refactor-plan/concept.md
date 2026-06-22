---
type: concept
name: refactor-plan-concept
feature: refactor-plan
depth: concept
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Refactor Plan

A refactor plan scans a codebase for structural problems and produces a prioritized roadmap — with effort estimates and risk levels — so you know which changes to make first and why.

## How the workflow runs

`RefactorPlanWorkflow` orchestrates three specialized subagents in sequence: `debt-scanner`, `impact-analyzer`, and `plan-generator`. Each subagent focuses on its own domain and reports findings as structured markdown. Once all three finish, the workflow synthesizes their output into a single report.

You call the workflow through its `execute()` method, which returns a `WorkflowResult`. The report formatting step — handled by `format_refactor_plan_report(result, input_data)` — converts that result into a human-readable document structured around three sections:

| Section | What it contains |
|---|---|
| **Summary** | Overall tech debt score (0–100) and a 2–3 sentence executive summary |
| **Refactoring** | Prioritized opportunities, each tagged with effort (small / medium / large) and risk (low / medium / high) |
| **Suggestions** | Actionable next steps ordered by priority, from quick wins to longer-term improvements |

The separation between `RefactorPlanWorkflow` and `format_refactor_plan_report` means the raw result is available for programmatic use before any formatting is applied — useful if you want to filter or re-rank items before presenting them.

## What the subagents look for

The `debt-scanner` subagent surfaces issues in categories like long methods, god classes, high cyclomatic complexity, deep nesting, copy-pasted blocks, circular imports, and dead code. The `impact-analyzer` then weighs each finding against how many files it touches and how much improvement a fix would deliver. The `plan-generator` uses that scoring to sort items so that high-severity, low-effort, high-impact changes appear at the top and risky changes are explicitly flagged.

## When it matters

Run a refactor plan when a module feels hard to change or test, before extending a tangled area with new features, or when you need concrete data to justify refactoring time to stakeholders. Because the roadmap is prioritized, you can stop at any point and still have addressed the highest-value items — avoiding the yak-shaving that comes from refactoring without a plan.

## Entry points

| Symbol | Role |
|---|---|
| `RefactorPlanWorkflow.execute()` | Runs the full three-subagent analysis and returns a `WorkflowResult` |
| `format_refactor_plan_report(result, input_data)` | Formats a `WorkflowResult` dict as a human-readable report |
| `main()` | CLI entry point that wires the two together for command-line use |
