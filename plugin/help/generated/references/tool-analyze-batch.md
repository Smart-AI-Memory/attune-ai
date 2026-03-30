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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `requests` | array | List of tasks to process in batch | required |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
