---
type: reference
subtype: tabular
name: tool-telemetry-stats
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Telemetry Stats

Get telemetry statistics. Shows cost savings, cache hit rates, and workflow performance.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `days` | integer | Number of days to analyze |  | 30 |

## Usage

`telemetry_stats()`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Attune Get Level — Get current interaction level (1-5). Level 1=Reactive, 2=Gui...
