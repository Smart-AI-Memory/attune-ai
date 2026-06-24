---
type: comparison
name: plugin-comparison
feature: plugin
depth: comparison
generated_at: 2026-06-24T05:04:42.110775+00:00
source_hash: db043c60a7143c7669b27c81b171e2b6169746b1daae7d276d9b914b20fb8c53
status: generated
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
