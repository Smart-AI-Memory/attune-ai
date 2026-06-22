---
name: lookup-warn
description: "Get context warnings for a file based on its extension and name. Surfaces known gotchas before the user hits them. Triggers on: warn me, gotchas, pitfalls, what should I watch out for, check this file."
argument-hint: "<file-path>"
---

# Lookup Warn

File-context warnings for the file the user is editing or
about to edit. Uses the `lookup_warn` MCP tool, which maps
the file extension and name to relevant tags and returns
the top N matching warning and task templates.

## When to use

- User is about to edit a file and wants to know the pitfalls
- User asks "what should I watch out for" on a specific file
- IDE selection changed — proactively surface warnings

## Scoping

If no file path is provided, use `AskUserQuestion`:

```yaml
question: "Which file should I check?"
header: "lookup-warn"
options:
  - label: "The file I'm currently viewing"
    description: "Use the IDE selection (if one is active)"
  - label: "A different file"
    description: "Provide a path relative to the project root"
```

If an IDE selection is available, prefer it without asking.

## Execution

1. Call the MCP tool `lookup_warn` with:
   - `file_path` — the user's file
   - `max_results` — 3 by default, or what the user asked for
   - `template_dir` — `.help/templates` if the project has one,
     otherwise omit
2. If `count` is 0, tell the user there are no known warnings
   for this file type and suggest running `lookup-list` to
   browse topics manually.
3. Print each entry in the `warnings` array as a list item.

## Output Format

```markdown
## Warnings for `<file-path>`

3 relevant topics:

1. <first warning content>

2. <second warning content>

3. <third warning content>

*To look up any of these topics in more detail, say 'look up X'.*
```

Keep entries compact — the templates are already rendered.
Don't paraphrase the tool output.
