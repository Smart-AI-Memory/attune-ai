---
type: comparison
name: plugin-comparison
feature: plugin
depth: comparison
generated_at: 2026-06-24T12:40:17.276596+00:00
source_hash: b2da4bbb5a02defe23a5d626662d1309cad3c1d550e9fe54c614bf96cdf2c6f6
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
