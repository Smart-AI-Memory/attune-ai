---
type: reference
subtype: tabular
name: tool-doc-audit
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Doc Audit

Audit existing documentation for staleness, broken links, and drift from source code.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Project root path |  | . |

## Usage

`doc_audit()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Discovery Sweep — Run the discovery-sweep meta-workflow: fans out across all a...
