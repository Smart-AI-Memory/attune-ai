---
type: error
feature: refactor-plan
depth: error
generated_at: 2026-04-14T14:52:21.193918+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan errors

Failures that occur when analyzing codebases for tech debt and generating prioritized refactoring roadmaps through the Agent SDK workflow system.

## Common error signatures

- **WorkflowResult validation errors** — When subagent responses don't match expected structured markdown format
- **Subagent execution failures** — One of the three subagents (debt-scanner, impact-analyzer, plan-generator) fails to complete
- **Report formatting errors** — Issues parsing workflow results into human-readable output
- **CLI argument errors** — Invalid paths or missing required parameters when running the workflow

## Where errors originate

- `RefactorPlanWorkflow.execute()` — Orchestrates the three subagents and synthesizes their findings
- `format_refactor_plan_report()` — Transforms workflow results into structured markdown reports
- `main()` — CLI entry point that validates arguments and invokes the workflow

## How to diagnose

1. **Check subagent completion status.** The workflow depends on three specialized subagents completing successfully. If one fails, the entire synthesis step fails. Look for errors mentioning 'debt-scanner', 'impact-analyzer', or 'plan-generator' in the traceback.

2. **Verify codebase path accessibility.** The workflow analyzes codebases at specified paths. Permission errors or missing directories will cause the workflow to fail before subagent execution begins.

3. **Examine subagent output format.** The workflow expects subagents to return structured markdown with specific sections (Summary, Refactoring, Suggestions). If subagents return malformed output, report formatting will fail.

4. **Check Agent SDK configuration.** The RefactorPlanWorkflow inherits from Agent SDK classes. SDK connection issues or configuration problems will prevent subagent execution.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
