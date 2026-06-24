---
type: tip
name: plugin-tip
feature: plugin
depth: tip
generated_at: 2026-06-24T13:46:09.936892+00:00
source_hash: 0c448ba69ee8546bc76d88364bffc606531d666c64711912a8285967cb769da2
status: generated
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Notes & tips

- **Add the marketplace first.** `install` needs a registered
  marketplace to resolve `attune-ai@attune-ai` against.
- **Mind the two names.** Marketplace `attune-ai-plugin`, plugin
  `attune-ai`. The install string repeats the plugin name on purpose.
- **The folders are the contract.** Claude Code discovers components by
  fixed folder names (`commands/`, `skills/`, `agents/`, `hooks/`,
  `help/`) — that layout *is* the plugin's interface.
- **Go to the component's feature to debug it.** MCP tools → mcp-server;
  hook behavior → hooks. This page is the bundle.
