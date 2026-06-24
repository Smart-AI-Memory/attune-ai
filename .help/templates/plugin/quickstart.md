---
type: quickstart
name: plugin-quickstart
feature: plugin
depth: quickstart
generated_at: 2026-06-24T13:46:09.936892+00:00
source_hash: 0c448ba69ee8546bc76d88364bffc606531d666c64711912a8285967cb769da2
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
