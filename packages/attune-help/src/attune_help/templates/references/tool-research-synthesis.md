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

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `sources` | array | List of document texts to synthesize (minimum 2) |  | required |
| `question` | string | Research question to answer |  | required |

## Usage

`research_synthesis(sources="...", question="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
