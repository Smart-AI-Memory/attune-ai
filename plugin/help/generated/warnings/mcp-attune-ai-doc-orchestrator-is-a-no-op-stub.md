---
type: warning
name: mcp-attune-ai-doc-orchestrator-is-a-no-op-stub
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub

## Condition

calling the MCP tool on a real project returns `{items_found: 0, docs_generated: [], docs_updated: [], total_cost: 0.0, phase: "complete", success: true}` — looks like a clean pass but did zero actual analysis

## Risk

Ignoring this guidance may cause: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub

## Mitigation

1. Don't trust a cost-zero MCP workflow response as evidence that work was attempted; verify by spot-checking the filesystem or running a direct script that's known to work

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub
