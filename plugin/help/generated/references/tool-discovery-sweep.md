---
type: reference
subtype: tabular
name: tool-discovery-sweep
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Discovery Sweep

Run the discovery-sweep meta-workflow: fans out across all audit sources (pattern scan, bug-predict, security, deps, perf, docs, tests), dedups, and triages findings into queue / questions / rejected buckets. Use for a full 'what should I fix' pass; single-purpose audits have their own tools (security_audit, bug_predict, deep_review).

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Directory or file to sweep |  | required |
| `budget_usd` | number | Total LLM spend cap (default 10.00) |  | 10.0 |
| `no_llm` | boolean | Fast pattern-only sweep (skip LLM sources) |  | False |

## Usage

`discovery_sweep(path="...")`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Code Review — Run code review workflow. Provides comprehensive code qualit...
