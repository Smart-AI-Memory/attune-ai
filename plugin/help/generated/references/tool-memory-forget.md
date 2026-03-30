---
type: reference
subtype: tabular
name: tool-memory-forget
category: tool
tags: [mcp, tool, memory]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Memory Forget

Remove data from attune-ai memory.

**Group:** memory

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `key` | string | Key or pattern_id to remove |  | required |
| `scope` | string | Scope of removal (default: all) | enum: session|persistent|all | all |

## Usage

`memory_forget(key="...")`

## Related Topics
- **Reference**: Tool: Memory Store — Store data in attune-ai memory. Use for structured knowledge...
- **Reference**: Tool: Memory Retrieve — Retrieve data from attune-ai memory by key or pattern ID.
- **Reference**: Tool: Memory Search — Search attune-ai memory for patterns matching a query.
