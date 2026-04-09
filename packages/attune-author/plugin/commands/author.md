---
name: author
description: Documentation authoring hub — generate, maintain, and validate help content
argument-hint: "[init | status | generate <feature> | maintain | docs <path>]"
---

Invoke the `author` skill from the attune-author plugin to handle this request.

User arguments: $ARGUMENTS

The `author` skill is the routing hub that dispatches to the
appropriate sub-skill based on the user's intent:

- `init` — bootstrap `.help/features.yaml` (author-init skill)
- `status` — report stale templates (author-status skill)
- `generate <feature>` — regenerate one feature (author-generate skill)
- `maintain` — regenerate all stale features (author-maintain skill)
- `docs <path>` — 3-stage AI doc pipeline (author-docs skill)

If no arguments are provided, the skill will use
`AskUserQuestion` to scope the request before executing.
