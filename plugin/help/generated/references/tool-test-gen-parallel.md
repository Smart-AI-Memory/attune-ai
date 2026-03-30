---
type: reference
subtype: tabular
name: tool-test-gen-parallel
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Test Gen Parallel

Batch-generate tests for 10-50 modules in parallel using multi-tier LLM orchestration.

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `top` | integer | Number of low-coverage modules to process | 200 |
| `batch_size` | integer | Modules to process concurrently per batch | 10 |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
