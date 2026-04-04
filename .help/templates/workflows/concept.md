---
feature: workflows
depth: concept
generated_at: 2026-04-04T02:25:50.272614+00:00
source_hash: 0d8b9057c8f6004f5eebcc6a44723afdac2c83eff80a405599ad678761baf5a3
status: generated
---

# Workflows

## What

AI-powered analysis workflows (security, code review, tests, etc.)

## Why

This feature provides workflows functionality for the project.

## How

Key components:

- `AgentRunResult` — Data extracted from Agent SDK execution.

- `AgentSDKResultAdapter` — Converts Agent SDK ResultMessage text into a WorkflowResult.

- `BaseWorkflow` — Base class for multi-model workflows.

- `BatchRequest` — Single request in a batch.

- `BatchResult` — Result from batch processing.
