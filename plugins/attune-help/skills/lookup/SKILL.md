---
name: lookup
description: "Look up help topics with progressive depth. Pair with attune-author for full author-and-read workflow. Triggers on: lookup, look up, depth, topic, help topic, tell me more."
argument-hint: "[topic or intent]"
---

# Lookup Hub

**IMPORTANT: Start your response by telling the user:**

> **Lookup Hub** — Read `.help/` templates with progressive
> depth. Companion to `/author` for author-and-read workflows.

## Scoping

If no argument is provided, use `AskUserQuestion`:

```yaml
question: "What would you like to do?"
header: "attune-help"
options:
  - label: "Look up a topic"
    description: "Progressive depth — concept, then task, then reference on repeat calls"
  - label: "List available topics"
    description: "Show all bundled or project-specific topics, optionally filtered by tag"
  - label: "Warn me about this file"
    description: "Show context warnings relevant to the file I'm editing"
```

## Execution

Map the user's intent to the right sub-skill:

| Input | Route to |
| ----- | -------- |
| "Look up X" or `<topic>` | lookup-topic skill |
| "Tell me more" or "deeper" | lookup-topic skill (repeat call advances depth) |
| "Start over" or "reset" | lookup-topic skill (calls `lookup_reset` first) |
| "List topics" or `list` | lookup-list skill |
| "What about this file" or `warn <path>` | lookup-warn skill |

## Natural Language Routing

| Pattern | Route to |
| ------- | -------- |
| "look up", "find topic", "open template" | lookup-topic skill |
| "list topics", "what's available", "browse help" | lookup-list skill |
| "warn me", "check this file", "gotchas for" | lookup-warn skill |

## MCP Tools

The plugin exposes these tools via the `attune-help` MCP server:

| Tool | Purpose |
| ---- | ------- |
| `lookup_topic` | Progressive depth lookup (concept -> task -> reference) |
| `lookup_list` | Enumerate available topics as a markdown table |
| `lookup_warn` | File-context warnings by extension and name |
| `lookup_preamble` | One-line "Use X when..." tooltip for a feature |
| `lookup_reset` | Clear session so next lookup starts at concept |

## MCP Server Not Running

If the MCP server is not responding, install the package
with the plugin extra and verify it's reachable:

```bash
pip install 'attune-help[plugin]'
python -m attune_help.mcp.server  # should start without errors
```

## Relationship to attune-ai and attune-author

- `/coach` (attune-ai) — full workflow coach with team memory
- `/lookup` (attune-help) — lightweight read-only topic lookup
- `/author` (attune-author) — writes templates that `/lookup` reads

`/lookup` is designed to coexist with `/coach`. Both can be
installed; Claude picks the right one based on trigger phrases.
