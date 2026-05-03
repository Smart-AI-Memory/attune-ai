---
name: audience-adaptation
source: src/attune/help/transformers.py
summary: This template demonstrates how a single structured source can be automatically
  transformed into different output formats (terminal, chat, documentation) through
  surface-specific render functions, eliminating content duplication across help channels.
tags:
- help-system
- architecture
type: concept
---

# Concept: Audience-Adaptive Rendering

The same template source produces different output depending on where the user accesses help. This means a single source of truth drives multiple surfaces without manual duplication.

## The Problem It Solves

Users access help in fundamentally different contexts, each with distinct needs:

- A **terminal user** benefits from color-coded panels and structured layout.
- A **Claude Code user** needs concise, conversational Markdown that fits inline in a chat.
- A **docs browser** expects full navigation, cross-references, and static site structure.

Maintaining separate copies of each help topic for each surface would create drift and increase maintenance overhead. Audience-adaptive rendering solves this by transforming a single source into the appropriate format at output time.

## How It Works

Three render functions in `transformers.py` handle the transformation:

| Function | Target surface | Key behavior |
|---|---|---|
| `render_claude_code()` | Claude Code inline chat | Strips Related Topics; truncates to conversational length |
| `render_marketplace()` | Static documentation site | Injects YAML frontmatter for SSG consumption |
| `render_cli()` | Rich terminal output | Renders panels, tables, and ANSI color via Rich |

Each function receives the same parsed template and applies surface-specific rules. The template itself contains no rendering logic — it only holds structured content.

## Key Design Decision

Rendering decisions live entirely in `transformers.py`, not in the templates. This keeps templates readable and ensures that changing the output format for a surface requires editing exactly one function.

## Related Topics

_No related topics yet._
