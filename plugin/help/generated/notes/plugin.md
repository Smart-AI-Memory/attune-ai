---
name: plugin
source: content/features/plugin.md
tags:
- plugin
- claude-code
type: note
---

# The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers

## Overview

The **plugin** is how attune installs into Claude Code. It is a
**bundle** — a directory under `plugin/` with a manifest and a set of
component folders that Claude Code discovers automatically when the
plugin is installed. It is a packaging artifact, not a Python API:
`plugin/core` carries only a `__version__`.

This page documents the **bundle itself** — its manifest
(`plugin.json`), its marketplace listing (`marketplace.json`), how a
user installs it, and the component directories Claude Code reads. It
does **not** document the MCP server internals (that is the
**mcp-server** feature) or the individual hook scripts (that is the
**hooks** feature); the plugin just *ships* those.

You reach it these ways:

- **install** — `claude plugin marketplace add
  Smart-AI-Memory/attune-ai` then `claude plugin install
  attune-ai@attune-ai`; Claude Code reads the manifest and registers
  every component;
- **inspect** — the `plugin/` directory: `plugin/.claude-plugin/` holds
  the two manifests, and the sibling folders (`commands/`, `skills/`,
  `agents/`, `hooks/`, `help/`) are the auto-discovered components.

## Concepts

### The two manifests

The bundle is described by two JSON files in
`plugin/.claude-plugin/`:

- **`plugin.json`** — the plugin manifest. Its `name` is `attune-ai`,
  with `version`, `description`, `author`, `homepage`, `repository`,
  `license` (`Apache-2.0`), and `keywords`. This is what Claude Code
  reads to register the plugin.
- **`marketplace.json`** — the marketplace listing. Its top-level
  `name` is **`attune-ai-plugin`** (the marketplace name, distinct from
  the plugin name), with an `owner` and `metadata`, and a `plugins`
  array. The single entry has `name` `attune-ai`, `source` `./` (the
  plugin lives at the marketplace root), `category` `developer-tools`,
  and its own `tags`.

The marketplace name (`attune-ai-plugin`) and the plugin name
(`attune-ai`) are deliberately different — the install command
(`attune-ai@attune-ai`) references the *plugin* name twice (plugin @
marketplace), because this repo is its own single-plugin marketplace.

### Auto-discovered components

Claude Code reads fixed-name folders inside the bundle. Each is a
component type:

| Folder | What it holds | Count |
|--------|---------------|-------|
| `commands/` | Slash commands (`.md`) | 1 (`handoff`) |
| `skills/` | Skills (one dir each, `SKILL.md`) | 17 |
| `agents/` | Subagent definitions (`.md`) | 6 |
| `hooks/` | `hooks.json` + hook scripts | ~20 scripts |
| `help/` | Generated help, templates, schemas | — |
| `.mcp.json` | MCP server registration | 1 server |

`commands/` ships `handoff` (the `/handoff` resume-prompt command).
The 17 skills are the developer-workflow surface (`spec`,
`security-audit`, `code-quality`, `smart-test`, `release-prep`, …). The
6 agents are read-only or planning subagents
(`security-reviewer`, `refactor-planner`, `release-prep-auditor`,
`spec-author`, `setup-guide`, `help-content-explainer`).

### Hooks and MCP — shipped, not owned here

`hooks/hooks.json` wires hook scripts to five Claude Code lifecycle
events — `SessionStart`, `Stop`, `PreToolUse`, `PostToolUse`,
`UserPromptSubmit`. `.mcp.json` registers the MCP server
(`uvx --from attune-ai python -m attune.mcp.server`). The plugin
**bundles** both, but their behavior is documented by the **hooks** and
**mcp-server** features respectively — this page covers only that they
are part of the bundle.

### The bundled core

`plugin/core/` exists so the plugin can carry a version for standalone
operation; `plugin/core/__init__.py` is just
`__version__ = "8.9.1"`. The real runtime is the pip-installed
`attune-ai` package, which the `.mcp.json` server pulls via
`uvx --from attune-ai`.

## Notes & tips

- **Add the marketplace first.** `install` needs a registered
  marketplace to resolve `attune-ai@attune-ai` against.
- **Mind the two names.** Marketplace `attune-ai-plugin`, plugin
  `attune-ai`. The install string repeats the plugin name on purpose.
- **The folders are the contract.** Claude Code discovers components by
  fixed folder names (`commands/`, `skills/`, `agents/`, `hooks/`,
  `help/`) — that layout *is* the plugin's interface.
- **Go to the component's feature to debug it.** MCP tools → mcp-server;
  hook behavior → hooks. This page is the bundle.
