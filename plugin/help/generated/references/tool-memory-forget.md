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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `key` | string | Key or pattern_id to remove | required |
| `scope` | string | Scope of removal (default: all) | all |

## Related Topics
- Reference: Related memory tools: memory_store, memory_retrieve, memory_search
