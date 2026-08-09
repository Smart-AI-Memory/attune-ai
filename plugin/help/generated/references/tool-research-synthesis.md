---
type: reference
subtype: tabular
name: tool-research-synthesis
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Research Synthesis

Synthesize insights from local source documents at a path. A 3-agent pipeline summarizes, analyzes patterns across, and produces a unified answer from the documents found at the given directory or file.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Directory or file of source documents to analyze |  | . |
| `depth` | string | Synthesis depth / agent budget (default: standard) | enum: quick|standard|deep | standard |

## Usage

`research_synthesis()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Discovery Sweep — Run the discovery-sweep meta-workflow: fans out across all a...
