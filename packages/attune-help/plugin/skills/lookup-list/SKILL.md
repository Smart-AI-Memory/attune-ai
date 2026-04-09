---
name: lookup-list
description: "List all available help topics, optionally filtered by tag. Use to browse what's in the bundled templates or the project's .help/ directory. Triggers on: list topics, what's available, browse help, show topics."
argument-hint: "[tag]"
---

# Lookup List

Enumerate available help topics as a grouped markdown table.
Uses the `lookup_list` MCP tool, which reads the
`cross_links.json` index for the active template directory.

## When to use

- User asks "what topics are available"
- User is exploring and doesn't know exact slug names
- User wants to filter by a specific tag (e.g. "show me all security topics")

## Scoping

Always ask about scope first — the unfiltered list is long:

```yaml
question: "How should I narrow the list?"
header: "lookup-list"
options:
  - label: "All topics"
    description: "Show everything, grouped by category (concepts, tasks, references, etc.)"
  - label: "Filter by tag"
    description: "Pick a tag like python, security, ci, testing"
  - label: "Just one category"
    description: "concepts, tasks, references, warnings, or another category"
```

If the user picks "filter by tag", ask for the tag name via
a second `AskUserQuestion`.

## Execution

1. Call the MCP tool `lookup_list` with:
   - `tag` — optional tag filter from scoping
   - `limit` — default 100, or what the user asked for
   - `template_dir` — `.help/templates` if the project has one
2. Render the response as a grouped markdown table (one
   section per category).
3. After the list, mention how to drill in: "Say 'look up X'
   for any topic you want to read."

## Output Format

```markdown
## Available Topics

**Total:** 557 (showing 100)
**Filter:** tag=python

### Concepts (43)

- con-audience-adaptation
- con-progressive-depth
- ...

### Tasks (40)

- tas-task-api-endpoint-design
- ...

### References (64)

- ref-claude-code-hooks
- ...
```

Sort entries alphabetically within each group. Don't show
categories that have no entries.
