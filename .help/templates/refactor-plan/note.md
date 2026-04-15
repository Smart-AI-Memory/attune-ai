---
type: note
feature: refactor-plan
depth: note
generated_at: 2026-04-14T14:53:29.703626+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Note: refactor plan

## Context

The refactor plan feature analyzes codebases to detect technical debt and generates prioritized refactoring roadmaps. It uses a multi-agent approach where specialized subagents scan for debt, analyze impact, and generate actionable plans.

## Architecture

The feature centers on `RefactorPlanWorkflow`, which coordinates three specialized subagents:

- **debt-scanner** — Identifies code smells and technical debt
- **impact-analyzer** — Assesses the risk and scope of potential changes
- **plan-generator** — Creates prioritized refactoring recommendations

The workflow produces structured reports with:
- Overall tech debt scores (0-100 scale)
- Prioritized refactoring opportunities with effort estimates (small/medium/large)
- Risk assessments (low/medium/high) for each recommended change
- Actionable next steps ordered by priority

## Implementation

The feature spans two modules:

- `RefactorPlanWorkflow` in `src/attune/workflows/refactor_plan.py` orchestrates the subagents using the Agent SDK
- `format_refactor_plan_report()` and `main()` in `src/attune/workflows/refactor_plan_report.py` handle report formatting and CLI access

The system prompt instructs the orchestrator to "be thorough but concise" and "cite file paths and line numbers when possible," emphasizing actionable specificity over general observations.

**Tags:** `refactor`, `tech-debt`, `complexity`
