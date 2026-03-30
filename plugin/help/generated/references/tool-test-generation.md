---
type: reference
subtype: tabular
name: tool-test-generation
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Test Generation

Generate tests for code. Can batch generate tests for multiple modules in parallel.

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `module` | string | Path to Python module | required |
| `batch` | boolean | Enable batch mode for parallel generation | False |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
