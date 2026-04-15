---
type: reference
feature: deep-review
depth: reference
generated_at: 2026-04-14T14:54:11.185553+00:00
source_hash: 97ad56b1e61d7e30b29c330d79cfa3d58efe35f1fa3640447d3cbf304737b484
status: generated
---

# Deep Review reference

## Classes

| Class | Description | Methods |
|-------|-------------|---------|
| `DeepReviewAgentSDKWorkflow` | Multi-pass deep code review using Claude Agent SDK subagents | `execute(self, **kwargs: Any) -> WorkflowResult` |

## Constants

| Constant | Value |
|----------|-------|
| `SUBAGENT_NAMES` | `{'security-reviewer', 'quality-reviewer', 'test-gap-reviewer'}` |
| `SYSTEM_PROMPT` | `'You are a senior code review orchestrator performing a multi-pass deep review. You coordinate three specialized subagents to produce a consolidated code review report. Be thorough but concise. Cite file paths and line numbers.'` |
| `TASK_PROMPT_TEMPLATE` | Template for review tasks that includes instructions for subagent coordination and report formatting with Summary, Security, Quality, Test Gaps, and Suggestions sections |

## Source files

- `src/attune/workflows/deep_review.py`

## Tags

`review`, `security`, `quality`, `tests`
