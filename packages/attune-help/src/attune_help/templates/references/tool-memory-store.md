---
type: reference
subtype: tabular
name: tool-memory-store
category: tool
tags: [mcp, tool, memory]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Memory Store

Store data in attune-ai memory. Use for structured knowledge, patterns, and cross-agent coordination. For simple preferences, recommend CLAUDE.md instead.

**Group:** memory

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `key` | string | Unique identifier for the stored data |  | required |
| `value` | string | Content to store |  | required |
| `classification` | string | Security classification (default: PUBLIC) | enum: PUBLIC|INTERNAL|SENSITIVE | PUBLIC |
| `pattern_type` | string | Category for pattern matching (optional) |  |  |

## Usage

`memory_store(key="...", value="...")`

## Related Topics
- **Reference**: Tool: Memory Retrieve — Retrieve data from attune-ai memory by key or pattern ID.
- **Reference**: Tool: Memory Search — Search attune-ai memory for patterns matching a query.
- **Reference**: Tool: Memory Forget — Remove data from attune-ai memory.
