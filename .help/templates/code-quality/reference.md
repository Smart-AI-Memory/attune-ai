---
type: reference
feature: code-quality
depth: reference
generated_at: 2026-05-04T02:24:34.493990+00:00
source_hash: 0d2aa6913a2dae27ec39d314c14f1f9a65365582fb2ba40d7060f571d73ca77e
status: generated
---

# Code Quality reference

Analyze code for style violations, correctness issues, potential bugs, and architectural problems using specialized review agents.

## Classes

| Class | Description |
|-------|-------------|
| `CodeReviewWorkflow` | SDK-native code review with four specialized subagents |

### CodeReviewWorkflow

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `**kwargs: Any` | `None` | Initialize the code review workflow |
| `execute` | `**kwargs: Any` | `WorkflowResult` | Run the multi-agent code review process |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_SUBAGENT_NAMES` | `{'security-reviewer', 'quality-reviewer', 'perf-reviewer', 'architect-reviewer'}` | Names of the four specialized review agents |
| `_SYSTEM_PROMPT` | `'You are a senior code review orchestrator. You coordinate four specialized subagents to produce a unified code review report. Be thorough but concise. Cite file paths and line numbers when possible.'` | System prompt for the orchestrating agent |
| `_TASK_PROMPT_TEMPLATE` | `'Review the codebase at {path} using the four specialized subagents below. Each subagent should focus on its domain and report findings as structured markdown.\n\nAfter all subagents finish, synthesize their findings into a single report with these sections:\n\n## Summary\nOverall code health score (0-100) and a 2-3 sentence executive summary.\n\n## Security\nFindings from the security reviewer.\n\n## Quality\nFindings from the quality reviewer.\n\n## Performance\nFindings from the performance reviewer.\n\n## Architecture\nFindings from the architecture reviewer.\n\n## Suggestions\nActionable next steps ordered by priority.'` | Template for structuring the multi-agent review task |

## Source files

- `src/attune/workflows/code_review.py`
- `src/attune/workflows/code_review_*.py`

## Tags

`review`, `quality`, `bugs`, `lint`
