---
name: author-init
description: "Initialize a .help/ documentation system in a project. Scans source directories for features and creates features.yaml. Triggers on: init help, set up help, bootstrap docs, scan project for features."
argument-hint: "[project-root]"
---

# Author Init

Bootstrap a `.help/` documentation system in a project by
scanning source directories and creating an initial
`features.yaml` manifest.

## When to use

- Setting up documentation for the first time
- Adding `.help/` to an existing project
- Re-scanning after a major restructure (manual review
  required)

## Scoping

Use `AskUserQuestion` to confirm:

```yaml
question: "Which directory should I scan and initialize?"
header: "Init"
options:
  - label: "Current directory"
    description: "Scan and create .help/ here"
  - label: "Specific path"
    description: "I'll provide a project root path"
```

## Execution

1. Call the MCP tool `author_init` with the chosen
   `project_root`.
2. Show the discovered features (name, description,
   confidence, files).
3. Ask the user to review `.help/features.yaml` and edit
   it before generating templates.
4. Suggest the next step: `author-generate` for one
   feature, or `author-maintain` to generate all.

## Output

```text
Initialized .help/features.yaml with N features:
  + auth — Authentication module (3 files)
  ~ utils — Utility helpers (5 files)
  ? scripts — Build scripts (1 file)

Edit .help/features.yaml to refine, then run:
  author-generate <feature>
```

Confidence markers: `+` high, `~` medium, `?` low.
