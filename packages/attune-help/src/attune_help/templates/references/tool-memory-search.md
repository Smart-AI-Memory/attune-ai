---
type: reference
subtype: tabular
name: tool-memory-search
category: tool
tags: [mcp, tool, memory]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Memory Search

Search attune-ai memory for patterns matching a query.

**Group:** memory

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `query` | string | Search string |  | required |
| `pattern_type` | string | Filter by pattern type (optional) |  |  |

## Usage

`memory_search(query="...")`

## Related Topics
- **Reference**: Tool: Memory Store — Store data in attune-ai memory. Use for structured knowledge...
- **Reference**: Tool: Memory Retrieve — Retrieve data from attune-ai memory by key or pattern ID.
- **Reference**: Tool: Memory Forget — Remove data from attune-ai memory.
