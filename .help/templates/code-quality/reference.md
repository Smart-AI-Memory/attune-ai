---
type: reference
feature: code-quality
depth: reference
generated_at: 2026-04-19T18:45:47.524501+00:00
source_hash: 44a3613be3cabe60572ba20a4d4a482a2b2727856106c44e43c6eafd7e2cc42e
status: generated
---

# Code Quality reference

Analyze code across multiple dimensions — style, correctness, likely bugs, and architecture — through specialized review agents.

## Classes

| Class | Description |
|-------|-------------|
| `CodeReviewWorkflow` | Coordinates four specialized subagents to produce unified code review reports |

### CodeReviewWorkflow

SDK-native code review with four specialized subagents.

#### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the code review workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the complete code review process |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_SUBAGENT_NAMES` | `'security-reviewer'`, `'quality-reviewer'`, `'perf-reviewer'`, `'architect-reviewer'` | The four specialized review agents |
| `_SYSTEM_PROMPT` | `'You are a senior code review orchestrator. You coordinate four specialized subagents to produce a unified code review report. Be thorough but concise. Cite file paths and line numbers when possible.'` | Main orchestrator prompt |
| `_TASK_PROMPT_TEMPLATE` | Template with sections for Summary, Security, Quality, Performance, Architecture, and Suggestions | Review report structure |

## Source files

- `src/attune/workflows/code_review.py`

## Tags

`review`, `quality`, `bugs`
