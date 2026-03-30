---
type: reference
subtype: tabular
name: tool-research-synthesis
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Research Synthesis

Synthesize insights from multiple documents. Summarizes, analyzes patterns, and produces a unified answer.

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `sources` | array | List of document texts to synthesize (minimum 2) | required |
| `question` | string | Research question to answer | required |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
