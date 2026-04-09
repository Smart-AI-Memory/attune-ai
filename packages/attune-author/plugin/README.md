# attune-author plugin

Documentation authoring tools for Claude Code. Generate,
maintain, and validate help content through natural
language.

```text
attune-help (reader) -> attune-author (authoring) -> attune-ai (full workflows)
```

## Install

```bash
# 1. Install the underlying Python package
pip install 'attune-author[plugin]'

# 2. Add the marketplace and install the plugin
claude plugin marketplace add Smart-AI-Memory/attune-ai
claude plugin install attune-author@attune-author-plugin
```

## Quick Start

Just describe what you want — the `author` skill routes
you to the right tool:

| You say | What happens |
| ------- | ------------ |
| "set up help in this project" | Scans for features and creates `.help/features.yaml` |
| "what's stale?" | Reports outdated templates |
| "regenerate the auth feature" | Generates concept/task/reference for `auth` |
| "refresh all stale templates" | Bulk regeneration in one pass |
| "write API docs for src/utils.py" | 3-stage AI doc generation |
| "look up the security feature" | Returns the concept template |

## Skills

| Skill | Purpose |
| ----- | ------- |
| `author` | Hub — Socratic discovery, routes to sub-skills |
| `author-init` | Bootstrap `.help/features.yaml` |
| `author-status` | Report stale features |
| `author-generate` | Generate templates for one feature |
| `author-maintain` | Regenerate all stale features |
| `author-docs` | Generate full docs from source via AI |

## MCP Tools

The plugin starts an MCP server (`attune-author`) that
exposes 6 tools:

| Tool | Wraps |
| ---- | ----- |
| `author_init` | `bootstrap.scan_project` + `manifest.save_manifest` |
| `author_status` | `staleness.check_staleness` |
| `author_generate` | `generator.generate_feature_templates` |
| `author_maintain` | `maintenance.run_maintenance` |
| `author_docs` | `doc_gen.generate_docs` (requires `[ai]`) |
| `author_lookup` | `manifest.resolve_topic` + reads template |

## Hooks

A non-blocking PostToolUse hook detects `git commit`
commands and surfaces stale-template suggestions via
stderr. You can ignore the suggestion or run
`/author maintain` to act on it.

## Agents

`doc-writer` — subagent for larger doc jobs that need
multiple turns or multiple output files. Used by the
`author-docs` skill when the target is a directory or
multi-file module.

## Requirements

- Python 3.10+
- `attune-author` Python package (installed automatically
  with the plugin)
- `ANTHROPIC_API_KEY` for the `author_docs` tool only —
  all other tools work without an API key

## Ecosystem

| Package | Role |
| ------- | ---- |
| `attune-help` | Lightweight reader (1 dep) |
| `attune-author` | Author, generate, maintain (4 deps) |
| `attune-ai` | Full developer workflow OS |

`attune-author` is the right choice if you want
documentation tooling without the full attune-ai
workflow stack.

## License

Apache 2.0
