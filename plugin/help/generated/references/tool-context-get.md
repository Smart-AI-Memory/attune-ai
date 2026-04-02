---
type: reference
subtype: tabular
name: tool-context-get
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Context Get

Get session context value.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `key` | string | Context key to retrieve |  | required |

## Usage

`context_get(key="...")`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
