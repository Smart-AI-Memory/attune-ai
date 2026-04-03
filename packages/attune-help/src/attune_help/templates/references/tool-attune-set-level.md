---
type: reference
subtype: tabular
name: tool-attune-set-level
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Attune Set Level

Set interaction level (1-5) for this session.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `level` | integer | Interaction level (1-5) | range: 1-5 | required |

## Usage

`attune_set_level(level="...")`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
