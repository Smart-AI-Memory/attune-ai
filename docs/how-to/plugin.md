# Plugin

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

## Tasks

### Install the plugin

**Goal:** add attune to Claude Code.

**Steps:**

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

**Verify:** the `/attune` and `/handoff` commands appear, and the
attune skills (`/spec`, `/security-audit`, …) are available in the
session. `attune-ai@attune-ai` is `plugin-name@marketplace-plugin` —
both resolve to the `attune-ai` plugin in this single-plugin
marketplace.

### Read the manifest

**Goal:** confirm the bundle's identity and version.

**Steps:**

```bash
cat plugin/.claude-plugin/plugin.json
```

**Verify:** `name` is `attune-ai`, `license` is `Apache-2.0`, and
`keywords` include `claude-code`. The `version` here is the plugin
bundle version (`8.9.0`); the sibling `marketplace.json` carries a
matching version in `metadata.version` and `plugins[0].version`.

### List the components Claude Code will discover

**Goal:** see what the bundle ships.

**Steps:**

```bash
ls plugin/commands   # 1 command (handoff.md)
ls plugin/skills     # 17 skill directories
ls plugin/agents     # 6 agent definitions
cat plugin/.mcp.json # the MCP server registration
```

**Verify:** each folder name is the component type Claude Code reads.
`hooks/hooks.json` binds scripts to the five lifecycle events; for what
those hooks do, see the **hooks** feature, and for the MCP server, the
**mcp-server** feature.

## Reference

The plugin is a packaging artifact; its "API" is the manifest schema
and the component folder layout.

### `plugin/.claude-plugin/plugin.json`

| Field | Value / Purpose |
|-------|-----------------|
| `name` | `attune-ai` — the plugin name. |
| `version` | Plugin bundle version (`8.9.0`). |
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

<!-- attune-generated: source_hash=db043c60a7143c7669b27c81b171e2b6169746b1daae7d276d9b914b20fb8c53 feature=plugin kind=how-to generated_at=2026-06-24 -->
