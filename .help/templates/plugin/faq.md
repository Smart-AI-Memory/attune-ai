---
type: faq
name: plugin-faq
feature: plugin
depth: faq
status: manual
---

# Plugin FAQ

## How do I install the attune plugin?

Two commands:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-ai@attune-ai
```

The first registers this repo as a Claude Code marketplace; the second
installs the `attune-ai` plugin from it. After install, Claude Code
auto-discovers the bundle's components and they become available in your
session.

## Why is the install string `attune-ai@attune-ai`?

It reads as `plugin-name@marketplace-plugin`. This repo is a
single-plugin marketplace named `attune-ai-plugin` that offers one
plugin, also named `attune-ai` — so the plugin name appears on both
sides of the `@`. The marketplace name (`attune-ai-plugin`) and the
plugin name (`attune-ai`) are deliberately different.

## What does the plugin actually contain?

A manifest plus auto-discovered component folders:

| Component | What's there |
|---|---|
| `commands/` | 1 slash command — `/handoff` |
| `skills/` | 17 skills (`/spec`, `/security-audit`, …) |
| `agents/` | 6 subagents |
| `hooks/` | `hooks.json` + the hook scripts |
| `help/` | the help bundle (`generated/`, `templates/`, `schemas/`) |
| `.mcp.json` | the MCP server registration |

The two manifests live in `plugin/.claude-plugin/` — `plugin.json`
(plugin identity) and `marketplace.json` (the marketplace listing).

## Is the plugin the same as the MCP server?

No. The plugin is the **bundle**; the MCP server is one component it
ships (registered in `.mcp.json`). The server itself — its tools,
transport, and rate limiting — is documented by the **mcp-server**
feature, not here.

## Does the plugin contain the runtime code?

No. `plugin/core/__init__.py` is just a `__version__`. The real runtime
is the pip-installed `attune-ai` package, which `.mcp.json` pulls at
launch with `uvx --from attune-ai python -m attune.mcp.server`.

## Why aren't the hooks documented here?

The plugin **ships** the hooks (`hooks/hooks.json` wires them to the
`SessionStart`, `Stop`, `PreToolUse`, `PostToolUse`, and
`UserPromptSubmit` events), but what each hook *does* is the **hooks**
feature's page. This page is about the bundle — manifest, install, and
the component layout Claude Code discovers.

**Tags:** `plugin`, `claude-code`
