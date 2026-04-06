---
feature: workflows
depth: concept
generated_at: 2026-04-06T02:39:03.074548+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Workflows

## What

Multi-model AI workflow templates that process tasks using specialized agents for security analysis, bug prediction, code review, and batch processing.

## When to use

Use workflows when you need to:

- Process multiple tasks efficiently with the Anthropic Batch API for 50% cost savings
- Run bug prediction analysis with specialized subagents
- Build complex multi-model pipelines with structured configuration
- Convert Agent SDK output into standardized workflow results

## Key components

| Component | Purpose |
|-----------|---------|
| `AgentRunResult` | Data extracted from Agent SDK execution. |
| `AgentSDKResultAdapter` | Converts Agent SDK ResultMessage text into a WorkflowResult. |
| `BaseWorkflow` | Base class for multi-model workflows. |
| `BatchRequest` | Single request in a batch. |
| `BatchResult` | Result from batch processing. |
| `BatchProcessingWorkflow` | Process multiple tasks via Anthropic Batch API (50% cost savings). |
| `BugPredictionWorkflow` | SDK-native bug prediction with three specialized subagents. |
| `WorkflowBuilder` | Builder for complex workflow configuration. |

## Related

workflows, ai, analysis
