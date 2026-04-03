---
type: reference
subtype: tabular
name: tool-bug-predict
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Bug Predict

Run bug prediction workflow. Analyzes code patterns and predicts potential bugs before they occur.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Path to directory or file to analyze |  | required |

## Usage

`bug_predict(path="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
- **Reference**: Tool: Test Generation — Generate tests for code. Can batch generate tests for multip...
