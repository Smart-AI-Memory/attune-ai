---
name: plugin
source: content/features/plugin.md
tags:
- plugin
- claude-code
type: task
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

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
bundle version (`8.9.2`); the sibling `marketplace.json` carries a
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
