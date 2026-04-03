---
type: reference
subtype: tabular
name: tool-auth-recommend
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Auth Recommend

Get authentication recommendation for a file. Analyzes LOC and suggests optimal auth mode.

**Group:** utility

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `file_path` | string | Path to file to analyze |  | required |

## Usage

`auth_recommend(file_path="...")`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
- **Reference**: Tool: Attune Get Level — Get current interaction level (1-5). Level 1=Reactive, 2=Gui...
