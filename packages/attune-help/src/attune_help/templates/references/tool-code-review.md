---
type: reference
subtype: tabular
name: tool-code-review
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Code Review

Run code review workflow. Provides comprehensive code quality analysis with suggestions for improvement.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Path to directory or file to review |  | required |

## Usage

`code_review(path="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Test Generation — Generate tests for code. Can batch generate tests for multip...
