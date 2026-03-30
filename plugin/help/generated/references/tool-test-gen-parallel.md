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

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `top` | integer | Number of low-coverage modules to process |  | 200 |
| `batch_size` | integer | Modules to process concurrently per batch |  | 10 |

## Usage

`test_gen_parallel()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
