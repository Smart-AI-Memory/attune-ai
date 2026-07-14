---
type: faq
name: plugin-faq
feature: plugin
depth: faq
generated_at: 2026-07-14T15:58:56.832425+00:00
source_hash: 0c448ba69ee8546bc76d88364bffc606531d666c64711912a8285967cb769da2
status: generated
---

# Plugin FAQ

## How do I install the attune plugin?

`claude plugin marketplace add Smart-AI-Memory/attune-ai`,
then `claude plugin install attune-ai@attune-ai`. The first adds the
marketplace; the second installs the plugin.

## Why is the install string `attune-ai@attune-ai`?

It's `plugin-name@marketplace-plugin`. This repo is a
single-plugin marketplace named `attune-ai-plugin`, offering the
`attune-ai` plugin — so the plugin name appears on both sides.

## What does the plugin actually contain?

A manifest plus auto-discovered components: 1 slash command
(`/handoff`), 17 skills, 6 agents, the hook scripts, the help bundle,
and an `.mcp.json` that registers the MCP server.

## Is the plugin the same as the MCP server?

No. The plugin is the bundle; the MCP server is one component
it ships (`.mcp.json`). The server is documented by the mcp-server
feature.

## Does the plugin contain the runtime code?

No — `plugin/core` is just a `__version__`. The runtime is the
pip-installed `attune-ai` package, which `.mcp.json` pulls with
`uvx --from attune-ai`.
