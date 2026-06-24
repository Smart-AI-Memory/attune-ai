---
type: troubleshooting
name: plugin-troubleshooting
feature: plugin
depth: troubleshooting
generated_at: 2026-06-24T05:04:42.110775+00:00
source_hash: db043c60a7143c7669b27c81b171e2b6169746b1daae7d276d9b914b20fb8c53
status: generated
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Failure modes

| Symptom | Cause | Fix | Severity |
|---|---|---|---|
| `claude plugin install attune-ai@attune-ai` can't find the plugin | The marketplace wasn't added first | Run `claude plugin marketplace add Smart-AI-Memory/attune-ai` before installing | high |
| Components don't appear after install | A component folder or the manifest is malformed | Confirm `plugin/.claude-plugin/plugin.json` parses and the folders exist | high |
| MCP tools missing but skills present | The `.mcp.json` server didn't launch (`uvx`/`attune-ai` unavailable) | See the mcp-server feature; confirm `uvx --from attune-ai python -m attune.mcp.server` runs | medium |
| Hooks not firing | `hooks/hooks.json` event wiring | See the hooks feature; this page only confirms the file is shipped | medium |
| Version looks stale | `plugin/core/__init__.py` / manifest version not bumped at release | The plugin version is set at release; the runtime is the pip `attune-ai` | low |

### Risk areas

- **Marketplace before install.** `install` resolves the plugin from a
  registered marketplace — adding the marketplace is the required first
  step.
- **Two names, not one.** `attune-ai-plugin` (marketplace) ≠
  `attune-ai` (plugin). The install string is `plugin@marketplace`,
  which here reads `attune-ai@attune-ai`.
- **The bundle ships, it doesn't implement.** MCP-server and hook
  behavior live in their own features; debugging those means going
  there, not here.

### Diagnosis order

1. Confirm the marketplace was added: `claude plugin marketplace add
   Smart-AI-Memory/attune-ai`.
2. Confirm the manifest parses: `cat
   plugin/.claude-plugin/plugin.json`.
3. Confirm the component folders exist: `ls plugin/skills
   plugin/agents plugin/commands`.
4. For missing MCP tools, go to the mcp-server feature; for hooks, the
   hooks feature.
