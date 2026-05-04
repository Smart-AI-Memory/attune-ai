---
type: reference
feature: deep-review
depth: reference
generated_at: 2026-05-04T02:28:33.091892+00:00
source_hash: e32648187b67c25e74699fc7a341857694ff7edd49f5c3d2fd4b545c1bdf65e4
status: generated
---

# Deep Review reference

Orchestrate comprehensive code reviews through specialized security, quality, and test analysis workflows.

## Classes

| Class | Description |
|-------|-------------|
| `DeepReviewAgentSDKWorkflow` | Multi-pass deep code review using Claude Agent SDK subagents |

### Methods

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `execute` | `self, **kwargs: Any` | `WorkflowResult` | Execute the multi-pass review workflow |

## Constants

| Constant | Values | Description |
|----------|--------|-------------|
| `_SUBAGENT_NAMES` | `{'security-reviewer', 'quality-reviewer', 'test-gap-reviewer'}` | Specialized reviewers for each analysis domain |
| `_SYSTEM_PROMPT` | `'You are a senior code review orchestrator performing a multi-pass deep review. You coordinate three specialized subagents to produce a consolidated code review report. Be thorough but concise. Cite file paths and line numbers.'` | System prompt for the orchestrator agent |
| `_TASK_PROMPT_TEMPLATE` | `'Review the codebase at {path} using the three specialized subagents below. Each subagent focuses on a specific domain and will report findings independently.\n\nAfter all subagents finish, synthesize their findings into a single consolidated report with these sections:\n\n## Summary\nOverall code health score (0-100) and a 2-3 sentence executive summary. Include counts of findings by severity.\n\n## Security\nFindings from the security reviewer, ordered by severity.\n\n## Quality\nFindings from the quality reviewer, ordered by severity.\n\n## Test Gaps\nFindings from the test gap reviewer, ordered by priority.\n\n## Suggestions\nTop 5-10 actionable next steps ordered by impact. Each suggestion should reference the specific finding it addresses.'` | Template for coordinating subagent reviews |

## Tags

`review`, `security`, `quality`, `tests`, `comprehensive-review`
