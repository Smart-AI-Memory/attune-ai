---
type: reference
name: refactor-plan-reference
feature: refactor-plan
depth: reference
generated_at: 2026-06-02T10:56:02.680417+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
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
