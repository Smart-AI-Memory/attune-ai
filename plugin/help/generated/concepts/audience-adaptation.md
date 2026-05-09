---
type: concept
name: audience-adaptation
tags: [help-system, architecture]
source: src/attune/help/transformers.py
---

# Concept: Audience-adaptive rendering

## What

The same template source produces different output for three channels: Claude Code (inline conversation), marketplace (static docs), and CLI (Rich terminal).

## Why

Users access help in different contexts. A terminal user needs color-coded panels; a Claude Code user needs concise markdown; a docs browser needs full navigation.

## How

Three render functions in transformers.py: render_claude_code() strips Related Topics and truncates; render_marketplace() adds YAML frontmatter for SSG; render_cli() uses Rich panels, tables, and color.

## Related Topics

_No related topics yet._
