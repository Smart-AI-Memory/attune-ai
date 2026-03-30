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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `key` | string | Unique identifier for the stored data | required |
| `value` | string | Content to store | required |
| `classification` | string | Security classification (default: PUBLIC) | PUBLIC |
| `pattern_type` | string | Category for pattern matching (optional) |  |

## Related Topics
- Reference: Related memory tools: memory_retrieve, memory_search, memory_forget
