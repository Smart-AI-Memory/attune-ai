---
type: reference
feature: refactor-plan
depth: reference
generated_at: 2026-05-04T02:28:07.797087+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Refactor Plan reference

Analyze code for structural problems and generate prioritized refactoring roadmaps using specialized subagents.

## Classes

| Class | Parameters | Description |
|-------|------------|-------------|
| `RefactorPlanWorkflow` | `**kwargs: Any` | Orchestrates debt scanning, impact analysis, and plan generation |

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `self, **kwargs: Any` | `None` | Initialize workflow with configuration |
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Run refactor planning analysis |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `format_refactor_plan_report` | `result: dict, input_data: dict` | `str` | Format analysis results into human-readable report |
| `main` | | `None` | CLI entry point for refactor planning workflow |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_SUBAGENT_NAMES` | `'debt-scanner'`, `'impact-analyzer'`, `'plan-generator'` | Specialized agents for refactor analysis |
| `_SYSTEM_PROMPT` | `'You are a senior refactoring plan orchestrator...'` | Orchestrator persona and instructions |
| `_TASK_PROMPT_TEMPLATE` | `'Analyze the codebase at {path} using...'` | Template for coordinating subagent analysis |

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

## Tags

`refactor`, `tech-debt`, `complexity`
