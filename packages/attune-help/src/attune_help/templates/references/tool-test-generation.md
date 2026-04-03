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

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `module` | string | Path to Python module |  | required |
| `batch` | boolean | Enable batch mode for parallel generation |  | False |

## Usage

`test_generation(module="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
