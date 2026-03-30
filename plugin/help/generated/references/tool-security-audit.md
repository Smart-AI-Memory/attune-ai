---
type: reference
subtype: tabular
name: tool-security-audit
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Security Audit

Run security audit workflow on codebase. Detects vulnerabilities, dangerous patterns, and security issues. Returns findings with severity levels.

## Parameters

| Parameter | Type | Description | Default |
| --------- | ---- | ----------- | ------- |
| `path` | string | Path to directory or file to audit | required |

## Related Topics
- Reference: Related workflow tools: bug_predict, code_review, test_generation
