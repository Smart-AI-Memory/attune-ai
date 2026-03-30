---
type: reference
subtype: tabular
name: tool-release-prep
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Release Prep

Run release preparation workflow. Checks health, security, changelog, and provides release recommendation.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Path to project root |  | . |

## Usage

`release_prep()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
