---
type: reference
name: refactor-plan-reference
feature: refactor-plan
depth: reference
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: a8b5dc570639e8d2770577c7a57611f86fbf596d547e3e6299cd6a5dd1281ea0
status: generated
---

# Refactor Plan reference

Scan code for structural problems and generate a prioritized refactoring roadmap.

## Classes

| Class | Description |
|-------|-------------|
| `RefactorPlanWorkflow` | Prioritize tech debt with Agent SDK subagents. |

### `RefactorPlanWorkflow`

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the workflow. |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the refactor plan workflow and return the result. |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_refactor_plan_report` | `result: dict, input_data: dict` | `str` | Format refactor plan output as a human-readable report. |
| `main` | — | `None` | CLI entry point for refactor planning workflow. |

## Constants

| Constant | Type | Members / Value |
|----------|------|-----------------|
| `_SUBAGENT_NAMES` | `list` | `'debt-scanner'`, `'impact-analyzer'`, `'plan-generator'` |
| `_SYSTEM_PROMPT` | `str` | `'You are a senior refactoring plan orchestrator. You coordinate three specialized subagents to produce a unified refactoring roadmap. Be thorough but concise. Cite file paths and line numbers when possible.'` |
| `_TASK_PROMPT_TEMPLATE` | `str` | `'Analyze the codebase at {path} using the three specialized subagents below. Each subagent should focus on its domain and report findings as structured markdown.\n\nAfter all subagents finish, synthesize their findings into a single report with these sections:\n\n## Summary\nOverall tech debt score (0-100) and a 2-3 sentence executive summary of the refactoring opportunities found.\n\n## Refactoring\nPrioritized list of refactoring opportunities with effort estimates (small/medium/large) and risk levels (low/medium/high) for each item.\n\n## Suggestions\nActionable next steps ordered by priority, including quick wins and longer-term improvements.'` |

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

## Tags

`refactor`, `tech-debt`, `complexity`
