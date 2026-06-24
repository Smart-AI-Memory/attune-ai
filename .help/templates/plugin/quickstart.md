---
type: quickstart
name: plugin-quickstart
feature: plugin
depth: quickstart
generated_at: 2026-06-24T05:04:42.110775+00:00
source_hash: db043c60a7143c7669b27c81b171e2b6169746b1daae7d276d9b914b20fb8c53
status: generated
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Quickstart

Install the plugin into Claude Code from the marketplace:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

The first command registers this repo as a marketplace; the second
installs the `attune-ai` plugin from it. After install, Claude Code
auto-discovers the components — the slash command, the 17 skills, the 6
agents, the hooks, and the MCP server — and they become available in
your session.

To inspect the bundle locally:

```bash
cat plugin/.claude-plugin/plugin.json
ls plugin/skills plugin/agents plugin/commands
```
