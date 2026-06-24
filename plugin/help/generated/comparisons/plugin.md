---
name: plugin
source: content/features/plugin.md
tags:
- plugin
- claude-code
type: comparison
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Comparison

The plugin is the **packaging surface**; the things it ships are
separate features:

| | plugin | mcp-server | hooks |
|--|--------|------------|-------|
| Role | The installable bundle (manifest + components) | One bundled component — the MCP tool server | One bundled component — lifecycle hook scripts |
| Artifact | `plugin/` + `plugin.json` / `marketplace.json` | `python -m attune.mcp.server` + `.mcp.json` | `hooks/hooks.json` + scripts |
| Documented by | This page | mcp-server feature | hooks feature |

The plugin is the box; mcp-server and hooks are two of the things
inside it. Install the box and Claude Code unpacks every component.
