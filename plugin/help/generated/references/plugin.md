---
name: plugin
source: content/features/plugin.md
tags:
- plugin
- claude-code
type: reference
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Reference

The plugin is a packaging artifact; its "API" is the manifest schema
and the component folder layout.

### `plugin/.claude-plugin/plugin.json`

| Field | Value / Purpose |
|-------|-----------------|
| `name` | `attune-ai` — the plugin name. |
| `version` | Plugin bundle version (`8.9.2`). |
| `description` | One-line plugin summary shown in Claude Code. |
| `author` | `{name, email}` — Smart AI Memory. |
| `homepage` / `repository` | Project links. |
| `license` | `Apache-2.0`. |
| `keywords` | Discovery keywords (include `claude-code`). |

### `plugin/.claude-plugin/marketplace.json`

| Field | Value / Purpose |
|-------|-----------------|
| `name` | `attune-ai-plugin` — the **marketplace** name. |
| `owner` | `{name, email}` of the marketplace. |
| `metadata` | `{description, version}`. |
| `plugins[]` | The plugin entries; one here. |
| `plugins[0].name` | `attune-ai` — the plugin offered. |
| `plugins[0].source` | `./` — plugin at the marketplace root. |
| `plugins[0].category` | `developer-tools`. |
| `plugins[0].tags` | Marketplace listing tags. |

### Component folders

| Folder | Component | Notes |
|--------|-----------|-------|
| `commands/` | Slash commands | `handoff.md` → `/handoff`. |
| `skills/` | Skills | 17 dirs, each with `SKILL.md`. |
| `agents/` | Subagents | 6 `.md` definitions. |
| `hooks/` | Hooks | `hooks.json` + ~20 scripts → 5 events. |
| `help/` | Help | `generated/`, `templates/`, `schemas/`. |
| `core/` | Version | `__version__` only. |
| `.mcp.json` | MCP server | `uvx --from attune-ai python -m attune.mcp.server`. |

### Install

| Step | Command |
|------|---------|
| Add marketplace | `claude plugin marketplace add Smart-AI-Memory/attune-ai` |
| Install plugin | `claude plugin install attune-ai@attune-ai` |
