---
type: reference
subtype: tabular
name: tool-release-notes
category: tool
tags: [mcp, tool, workflow]
source: src/attune/mcp/tool_schemas.py
---

# Reference: Tool: Release Notes

Run the release-notes advisory workflow. Drafts a changelog from git history and gives a go/no-go recommendation. Advisory only — not a gate; the deterministic 4-agent gate is CLI-only (attune workflow run release-gate).

**Group:** workflow

## Parameters

| Parameter | Type | Description | Constraints | Default |
| --------- | ---- | ----------- | ----------- | ------- |
| `path` | string | Path to project root |  | . |

## Usage

`release_notes()`

## Related Topics
- **Reference**: Tool: Security Audit — Run security audit workflow on codebase. Detects vulnerabili...
- **Reference**: Tool: Bug Predict — Run bug prediction workflow. Analyzes code patterns and pred...
- **Reference**: Tool: Discovery Sweep — Run the discovery-sweep meta-workflow: fans out across all a...
