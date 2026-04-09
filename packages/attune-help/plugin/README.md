# attune-help plugin

Lightweight help runtime for Claude Code. Reads `.help/`
templates with progressive depth, audience adaptation, and
renderer choices. No AI API keys required.

Pairs with [attune-author](../attune-author/plugin/) to give
you a complete author-and-read workflow without the full
[attune-ai](../../../plugin/) plugin.

## Install

From the monorepo marketplace:

```bash
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-help@attune-ai
```

Or for local testing:

```bash
claude --plugin-dir packages/attune-help/plugin
```

The plugin requires the `[plugin]` extra of the
`attune-help` library so the MCP server can start:

```bash
pip install 'attune-help[plugin]'
```

## Quick Start

Say any of these in Claude Code after installing:

- `look up progressive depth` — fetch the concept view
- `tell me more` — advance to the next depth level
- `list topics` — browse everything available
- `what should I watch out for in src/app.py` — file-context warnings
- `look up security` — start a new topic

## Skills

| Skill | What it does |
| ----- | ------------ |
| `lookup` | Hub — Socratic routing to the other skills |
| `lookup-topic` | Progressive depth lookup for one topic |
| `lookup-warn` | File-context warnings by extension and name |
| `lookup-list` | Enumerate available topics, grouped by category |

## MCP Tools

The plugin's MCP server exposes six tools prefixed with
`lookup_` to avoid colliding with attune-ai's `help_*` tools:

| Tool | Purpose |
| ---- | ------- |
| `lookup_topic` | Progressive depth lookup |
| `lookup_list` | Enumerate topics with optional tag filter |
| `lookup_warn` | Relevant warnings for a file path |
| `lookup_preamble` | One-line "Use X when..." tooltip |
| `lookup_reset` | Clear session so next lookup starts at concept |
| `lookup_status` | Read current depth level (read-only, no advance) |

## Ecosystem

Three plugins, one monorepo:

| Plugin | Role | Requires |
| ------ | ---- | -------- |
| `attune-ai` | Full workflow OS — 14 skills, security, tests, release prep | — |
| `attune-author` | Author .help/ templates — scan, generate, maintain, AI doc gen | Anthropic API key for `author_docs` |
| `attune-help` | Read .help/ templates with progressive depth | — |

You can install any combination. Common pairings:

- `attune-author` + `attune-help` — author-and-read without the workflow layer
- `attune-ai` only — the full experience including `/coach`, which plays a similar role to `/lookup`
- All three — `/lookup` and `/coach` coexist, each matches different natural-language triggers

## How it Works

`attune-help` ships 557 bundled templates (43 concepts, 40
tasks, 64 references, plus warnings, tips, comparisons, and
more). It also reads project-local templates from
`.help/templates/` when they exist, falling back to bundled
content when a topic is missing from the project.

Progressive depth is the core UX: the first call on a topic
returns the concept view (what is it, when to use it).
Repeat calls on the same topic escalate to the task view
(step-by-step), then the reference view (full detail). Say
"reset" or "start over" to go back to the concept view.

## Configuration

The plugin writes session state to
`~/.attune-help/sessions/` by default. To use a different
storage backend, configure your own `HelpEngine` in Python
and pass a custom `SessionStorage` implementation. The MCP
server always uses `LocalFileStorage` with default paths.

## Troubleshooting

If `/mcp` doesn't show the `attune-help` server after
installing, the MCP process logs to a file — nothing goes
to stdout so the JSON-RPC stream over stdio stays clean.
Check:

```text
$TMPDIR/attune-help/attune-help-mcp.log
```

On macOS that typically resolves to
`/var/folders/.../T/attune-help/attune-help-mcp.log`. On
Linux, `/tmp/attune-help/attune-help-mcp.log`. The file is
created on first start; if it's missing entirely, the
server process itself never launched — check that
`uv run --from 'attune-help[plugin]' python -m
attune_help.mcp.server` runs cleanly from a real shell.

## Related

- [attune-help library docs](../README.md)
- [attune-author plugin](../../attune-author/plugin/) — the authoring side
- [attune-ai plugin](../../../plugin/) — the full workflow suite
