---
type: reference
subtype: tabular
name: tool-list-capabilities
category: tool
tags: [mcp, tool, utility]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: List Capabilities

Enumerate everything attune offers, read live from the registries: every workflow (list_workflows), wizard (list_wizards), and registered MCP tool. Returns grouped name+description lists so a catalog never drifts from the code. Use to answer 'what can attune do?' / 'list all capabilities'. For routing to one workflow, use the attune-hub skill instead.

**Group:** utility

## Usage

`list_capabilities()`

## Related Topics
- **Reference**: Tool: Auth Status — Get authentication strategy status. Shows current configurat...
- **Reference**: Tool: Auth Recommend — Get authentication recommendation for a file. Analyzes LOC a...
- **Reference**: Tool: Telemetry Stats — Get telemetry statistics. Shows cost savings, cache hit rate...
