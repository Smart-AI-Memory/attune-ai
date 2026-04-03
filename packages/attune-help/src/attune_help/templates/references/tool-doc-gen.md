---
type: reference
subtype: tabular
name: tool-doc-gen
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Doc Gen

Generate new documentation from source code. Produces API references, guides, or READMEs.

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `source_path` | string | Path to source file to document |  | required |
| `doc_type` | string | Type of documentation (api_reference, guide, readme) |  | api_reference |
| `audience` | string | Target audience (developers, users, contributors) |  | developers |

## Usage

`doc_gen(source_path="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
