---
name: plugin
source: content/features/plugin.md
tags:
- plugin
- claude-code
type: tip
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
