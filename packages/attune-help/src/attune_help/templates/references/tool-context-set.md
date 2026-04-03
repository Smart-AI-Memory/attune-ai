---
type: reference
subtype: tabular
name: tool-context-set
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Context Set

Set session context value.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `key` | string | Context key |  | required |
| `value` | string | Context value |  | required |

## Usage

`context_set(key="...", value="...")`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
