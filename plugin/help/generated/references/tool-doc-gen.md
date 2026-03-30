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

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `source_path` | string | Path to source file to document | required |
| `doc_type` | string | Type of documentation (api_reference, guide, readme) | api_reference |
| `audience` | string | Target audience (developers, users, contributors) | developers |

## Related Topics
- Reference: Related workflow tools: security_audit, bug_predict, code_review
