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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `file_path` | string | Path to file to analyze | required |

## Related Topics
- Reference: Related utility tools: auth_status, telemetry_stats, attune_get_level
