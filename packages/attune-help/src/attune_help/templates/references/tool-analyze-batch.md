---
type: reference
subtype: tabular
name: tool-analyze-batch
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Analyze Batch

Submit tasks to the Anthropic Batch API for 50% cost savings. Processes asynchronously (up to 24 hours). Best for non-urgent bulk analysis.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `requests` | array | List of tasks to process in batch |  | required |

## Usage

`analyze_batch(requests="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
