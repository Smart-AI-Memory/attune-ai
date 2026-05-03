---
confidence: Verified
name: jinja2-trim-blocks-lstrip-blocks-eats-newlines-between
source: CLAUDE.md Lessons Learned
summary: This template documents how to resolve Jinja2 template rendering issues where
  `trim_blocks` and `lstrip_blocks` settings cause unintended newline removal between
  conditional blocks and adjacent content, and explains how to use the dash syntax
  for explicit whitespace control.
tags:
- git
type: error
---

# Error: Jinja2 `trim_blocks`/`lstrip_blocks` Removes Newlines Between Conditionals and Adjacent Lines

## Root Cause

When both `trim_blocks` and `lstrip_blocks` are enabled, a `{% if tags %}...{% endif %}` block placed on its own line causes the trailing newline to be consumed. This means the next line's content is concatenated directly onto the preceding output — for example, `tags: [x]source:` instead of `tags: [x]\nsource:`.

## Resolution

Use the dash (`-`) whitespace control syntax to manage newlines explicitly:

- `{%- if tags -%}` — strips whitespace before and after the opening tag
- `{%- endif -%}` — strips whitespace before and after the closing tag

Apply these selectively to preserve intended newlines while preventing unintended concatenation.

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

- Best practice: Jinja2 whitespace control with `trim_blocks` and `lstrip_blocks`
