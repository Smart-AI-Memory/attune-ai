---
type: faq
name: mcp-attune-ai-doc-orchestrator-is-a-no-op-stub
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about mcp__attune-ai__doc_orchestrator is a no-op stub?

## Answer

calling the MCP tool on a real project returns `{items_found: 0, docs_generated: [], docs_updated: [], total_cost: 0.0, phase: "complete", success: true}` — looks like a clean pass but did zero actual analysis. Don't trust a cost-zero MCP workflow response as evidence that work was attempted; verify by spot-checking the filesystem or running a direct script that's known to work.

## Related Topics
- **Error**: Detailed error: `mcp__attune-ai__doc_orchestrator` is a no-op
  stub
