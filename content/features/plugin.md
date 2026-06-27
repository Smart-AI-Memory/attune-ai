---
feature: plugin
summary: The Claude Code plugin bundle — its manifest, marketplace listing, install flow, and the components Claude Code auto-discovers
tags: [plugin, claude-code]
source_globs:
  - plugin/**
nav:
  help: plugin
  mkdocs:
    how-to: how-to/plugin
    architecture: architecture/plugin
    reference: reference/plugin
---

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
The 23 skills are the developer-workflow surface (`spec`,
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
`__version__ = "9.1.0"`. The real runtime is the pip-installed
`attune-ai` package, which the `.mcp.json` server pulls via
`uvx --from attune-ai`.

## Quickstart

Install the plugin into Claude Code from the marketplace:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

The first command registers this repo as a marketplace; the second
installs the `attune-ai` plugin from it. After install, Claude Code
auto-discovers the components — the slash command, the 23 skills, the 6
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
bundle version (`9.1.0`); the sibling `marketplace.json` carries a
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
| `version` | Plugin bundle version (`9.1.0`). |
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

## FAQ seeds

> **Channel-4 input, not a rendered FAQ.** The FAQ is a dynamic source
> of truth fed by four channels — unmatched user queries, telemetry
> error-frequency, GitHub issues, and these author-curated seeds —
> merged, deduplicated, and frequency-ranked by the FAQ Generator (see
> doc-stack D3, and the help-docs-single-source spec's decisions.md D6).
> This section is **not** projected verbatim as the FAQ; it contributes
> the feature's author-curated seed questions.

- **Q:** How do I install the attune plugin?
  **A:** `claude plugin marketplace add Smart-AI-Memory/attune-ai`,
  then `claude plugin install attune-ai@attune-ai`. The first adds the
  marketplace; the second installs the plugin.
- **Q:** Why is the install string `attune-ai@attune-ai`?
  **A:** It's `plugin-name@marketplace-plugin`. This repo is a
  single-plugin marketplace named `attune-ai-plugin`, offering the
  `attune-ai` plugin — so the plugin name appears on both sides.
- **Q:** What does the plugin actually contain?
  **A:** A manifest plus auto-discovered components: 1 slash command
  (`/handoff`), 23 skills, 6 agents, the hook scripts, the help bundle,
  and an `.mcp.json` that registers the MCP server.
- **Q:** Is the plugin the same as the MCP server?
  **A:** No. The plugin is the bundle; the MCP server is one component
  it ships (`.mcp.json`). The server is documented by the mcp-server
  feature.
- **Q:** Does the plugin contain the runtime code?
  **A:** No — `plugin/core` is just a `__version__`. The runtime is the
  pip-installed `attune-ai` package, which `.mcp.json` pulls with
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

## Design & extension

### Design decisions

- **Self-marketplace.** The repo is its own single-plugin marketplace
  (`source: ./`), so `marketplace add` + `install` point at one
  GitHub repo — no separate registry to publish to.
- **Convention over configuration.** Components are discovered by fixed
  folder names rather than enumerated in the manifest, keeping
  `plugin.json` to identity/metadata.
- **Thin bundled core.** `plugin/core` carries only a version; the
  heavy runtime stays in the pip package the MCP server pulls, so the
  bundle stays small and the runtime updates independently.
- **Separation of concerns.** The bundle ships the MCP server and hooks
  but documents them as their own features — the plugin page stays about
  packaging.

### Extension points

- **Add a command/skill/agent:** drop a file into the matching folder
  (`commands/*.md`, `skills/<name>/SKILL.md`, `agents/*.md`); Claude
  Code auto-discovers it on install.
- **Add a hook:** wire it in `hooks/hooks.json` (see the hooks
  feature).
- **Change marketplace metadata:** edit
  `plugin/.claude-plugin/marketplace.json` (name, category, tags).
- **Bump the bundle version:** update `plugin.json`,
  `marketplace.json`, and `plugin/core/__init__.py` together at
  release.
