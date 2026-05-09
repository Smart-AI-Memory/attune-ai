---
type: error
name: mcp-attune-ai-doc-orchestrator-is-a-no-op-stub
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub

## Signature

`mcp__attune-ai__doc_orchestrator` is a no-op
  stub

## Root Cause

calling the MCP tool on a real project returns `{items_found: 0, docs_generated: [], docs_updated: [], total_cost: 0.0, phase: "complete", success: true}` — looks like a clean pass but did zero actual analysis. Don't trust a cost-zero MCP workflow response as evidence that work was attempted; verify by spot-checking the filesystem or running a direct script that's known to work. For real doc gap analysis today, skip the MCP tools and do a direct `ast` parse + docstring check in Bash — takes seconds and actually returns signal.

## Resolution

1. calling the MCP tool on a real project returns `{items_found: 0, docs_generated: [], docs_updated: [], total_cost: 0.0, phase: "complete", success: true}` — looks like a clean pass but did zero actual analysis

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub
