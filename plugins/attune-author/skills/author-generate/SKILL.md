---
name: author-generate
description: "Generate concept, task, and reference templates for one feature using Jinja2 meta templates. Triggers on: generate template, regenerate feature, write help for, create docs for one feature."
argument-hint: "<feature-name>"
---

# Author Generate

Generate concept, task, and reference templates for a
single feature using Jinja2 meta templates and an optional
LLM polish pass (when `ANTHROPIC_API_KEY` is set).

## When to use

- After adding a new feature to `.help/features.yaml`
- After a feature's source code changes substantially
- When you want to overwrite a manual template
  (`overwrite=true`)

## Scoping

If no feature name is provided, use `AskUserQuestion` to
list features from `features.yaml`:

1. Read `.help/features.yaml` to enumerate features
2. Present them as options (max 4, with "Other" for
   manual entry if more)
3. Confirm the choice before calling the tool

## Execution

1. Call the MCP tool `author_generate` with `feature`,
   `help_dir`, `project_root`, and `overwrite` (default
   `false`).
2. List the generated template paths.
3. Suggest reading the templates with the user's editor
   or running `author-status` to confirm they're current.

## Output

```text
Generated 3 templates for 'auth':
  - .help/templates/auth/concept.md
  - .help/templates/auth/task.md
  - .help/templates/auth/reference.md
```

If a template has `status: manual` in frontmatter, it is
skipped unless `overwrite=true` is set.
