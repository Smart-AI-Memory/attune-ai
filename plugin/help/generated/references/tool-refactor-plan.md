---
type: reference
subtype: tabular
name: tool-refactor-plan
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Refactor Plan

Scan for tech debt, analyze trends, and generate a prioritized refactoring plan.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Directory to scan for refactoring opportunities |  | . |

## Usage

`refactor_plan()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
