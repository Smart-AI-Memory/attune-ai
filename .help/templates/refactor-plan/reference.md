---
type: reference
feature: refactor-plan
depth: reference
generated_at: 2026-04-14T14:52:13.028226+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Refactor Plan reference

## Classes

| Class | Description | Methods |
|-------|-------------|---------|
| `RefactorPlanWorkflow` | Prioritize tech debt with Agent SDK subagents | `__init__(**kwargs: Any) -> None`<br>`execute(**kwargs: Any) -> WorkflowResult` |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_refactor_plan_report` | `result: dict, input_data: dict` | `str` | Format refactor plan output as a human-readable report |
| `main` | none | `None` | CLI entry point for refactor planning workflow |

## Constants

| Constant | Type | Value |
|----------|------|-------|
| `_SUBAGENT_NAMES` | `list` | `{'debt-scanner', 'impact-analyzer', 'plan-generator'}` |
| `_SYSTEM_PROMPT` | `str` | `'You are a senior refactoring plan orchestrator. You coordinate three specialized subagents to produce a unified refactoring roadmap. Be thorough but concise. Cite file paths and line numbers when possible.'` |
| `_TASK_PROMPT_TEMPLATE` | `str` | `'Analyze the codebase at {path} using the three specialized subagents below. Each subagent should focus on its domain and report findings as structured markdown.\n\nAfter all subagents finish, synthesize their findings into a single report with these sections:\n\n## Summary\nOverall tech debt score (0-100) and a 2-3 sentence executive summary of the refactoring opportunities found.\n\n## Refactoring\nPrioritized list of refactoring opportunities with effort estimates (small/medium/large) and risk levels (low/medium/high) for each item.\n\n## Suggestions\nActionable next steps ordered by priority, including quick wins and longer-term improvements.'` |

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`
