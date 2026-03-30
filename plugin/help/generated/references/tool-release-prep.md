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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `path` | string | Path to project root | . |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
