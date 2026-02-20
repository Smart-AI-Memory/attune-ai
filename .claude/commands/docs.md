---
name: docs
description: Documentation generation and explanation
category: primary
aliases: [doc]
tags: [documentation, readme, changelog, explain]
version: "1.0.0"
question:
  header: "Docs action"
  question: "What documentation task do you need?"
  multiSelect: false
  options:
    - label: "Explain code"
      description: "Understand how code works"
    - label: "Generate docs"
      description: "Create or update documentation"
    - label: "Update README"
      description: "Update the project README"
    - label: "Generate changelog"
      description: "Create changelog from git history"
---

# docs

Documentation generation and code explanation.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `explain` | Explain how code works |
| `generate` | Generate documentation |
| `readme` | Update README |
| `changelog` | Generate changelog |
| `overview` | High-level project overview |

## Usage

```bash
/docs                   # Ask what to do
/docs explain           # Explain code
/docs generate          # Generate documentation
/docs readme            # Update README
/docs changelog         # Generate changelog
```

## Behavior

### explain

Use `AskUserQuestion` to scope:

- Which file, function, or module to explain?
- What level of detail? (overview, deep dive, or
  architecture)

Then read the code and provide a clear explanation
with context.

### generate

Use `AskUserQuestion` to scope:

- What to document? (API, module, function)
- Format? (docstrings, markdown, or both)

Then generate documentation using the codebase.

### readme

Read the current README and project structure, then
suggest or apply updates based on current state.

### changelog

Use git log to generate a changelog:

```bash
git log --oneline --since="last tag"
```

Format as a markdown changelog grouped by type
(features, fixes, refactoring).
