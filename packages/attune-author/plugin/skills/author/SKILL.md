---
name: author
description: "Documentation authoring hub — generate, maintain, and validate help content for your project. Triggers on: author, write docs, generate documentation, help system, stale templates, doc-gen, README, .help."
argument-hint: "<what you need>"
---

# Author Hub

**IMPORTANT: Start your response by telling the user:**

> **Author Hub** — Your starting point for documentation
> authoring — generates, maintains, and validates help
> content.

## Scoping

If no argument is provided, use `AskUserQuestion`:

```yaml
question: "What would you like to do with documentation?"
header: "attune-author"
options:
  - label: "Set up help system"
    description: "Bootstrap .help/features.yaml in this project"
  - label: "Check what's stale"
    description: "Find features with outdated templates"
  - label: "Generate or update templates"
    description: "Generate concept/task/reference templates for one or more features"
  - label: "Generate full docs from source"
    description: "Use AI to write API references, guides, or READMEs"
```

## Execution

Map the user's intent to the right sub-skill:

| Input | Route to |
| ----- | -------- |
| "Set up help system" or `init` | author-init skill |
| "Check what's stale" or `status` | author-status skill |
| "Generate templates" or `generate <feature>` | author-generate skill |
| "Update everything" or `maintain` | author-maintain skill |
| "Generate full docs" or `docs <path>` | author-docs skill |
| "Look up help on X" or `lookup <topic>` | call `author_lookup` MCP tool directly |

## Natural Language Routing

| Pattern | Route to |
| ------- | -------- |
| "init", "set up", "bootstrap", "scan project" | author-init skill |
| "stale", "status", "what changed", "outdated" | author-status skill |
| "generate template", "regenerate one feature" | author-generate skill |
| "regenerate all", "update all stale", "maintain" | author-maintain skill |
| "write docs", "API reference", "README", "guide" | author-docs skill |

## MCP Tools

The plugin exposes these tools via the `attune-author` MCP server:

| Tool | Purpose |
| ---- | ------- |
| `author_init` | Bootstrap `.help/features.yaml` from a project scan |
| `author_status` | Report stale and current features as markdown |
| `author_generate` | Generate templates for one feature |
| `author_maintain` | Regenerate all stale features in one pass |
| `author_docs` | 3-stage AI doc generation (outline → write → review) |
| `author_lookup` | Look up help for a topic by name or tag |

## MCP Server Not Running

If the MCP server is not responding, install the package
and verify it's reachable:

```bash
pip install 'attune-author[plugin]'
python -m attune_author.mcp.server  # should start without errors
```
