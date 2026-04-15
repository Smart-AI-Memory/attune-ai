---
type: reference
feature: code-quality
depth: reference
generated_at: 2026-04-14T14:40:46.697576+00:00
source_hash: b7e7be04c17fbc5cdc5e0ffa118eb0ba70c9043509d9f75f395c0c87cf29bbe5
status: generated
---

# Code Quality reference

## Classes

| Class | Description |
|-------|-------------|
| `CodeReviewWorkflow` | SDK-native code review with four specialized subagents |

### CodeReviewWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the code review workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Execute the four-stage code review process |

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `SUBAGENT_NAMES` | `{'security-reviewer', 'quality-reviewer', 'perf-reviewer', 'architect-reviewer'}` | Names of the four specialized review agents |
| `SYSTEM_PROMPT` | `'You are a senior code review orchestrator...'` | Base system prompt for the orchestrator agent |
| `TASK_PROMPT_TEMPLATE` | `'Review the codebase at {path}...'` | Template for review tasks with structured output format |
