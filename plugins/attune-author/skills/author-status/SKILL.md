---
name: author-status
description: "Report which feature templates are stale by comparing source file hashes. Triggers on: stale templates, what's outdated, doc status, check help freshness, what changed."
argument-hint: "[help-dir]"
---

# Author Status

Report which feature templates are stale by comparing the
SHA-256 hash of source files against the hash stored in
each template's frontmatter.

## When to use

- Before publishing a release — make sure docs match code
- After a refactor — see which features need attention
- Periodic maintenance — keep `.help/` in sync

## Scoping

If no `help_dir` is provided, default to `.help/` in the
current project. Use `AskUserQuestion` only if the path is
ambiguous (multiple `.help/` directories visible).

## Execution

1. Call the MCP tool `author_status` with `help_dir` and
   `project_root`.
2. Render the markdown report returned in the `report`
   field.
3. If stale features exist, suggest the next step:
   `author-maintain` to regenerate all, or
   `author-generate <feature>` for a single feature.

## Output

The MCP tool returns markdown like:

```markdown
## Help Status

**12** current, **3** stale

### Stale Features

| Feature | Description | Files Changed |
|---------|-------------|---------------|
| auth | Authentication and authorization | 5 source files |
| cli | Command-line interface | 2 source files |
```

Render this as-is — no further formatting needed.
