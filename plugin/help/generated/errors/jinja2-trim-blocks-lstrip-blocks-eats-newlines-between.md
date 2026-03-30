---
type: error
name: jinja2-trim-blocks-lstrip-blocks-eats-newlines-between
confidence: Verified
tags: [git]
source: CLAUDE.md Lessons Learned
---

# Error: Jinja2 `trim_blocks`/`lstrip_blocks` eats newlines between
  conditional and adjacent lines

## Signature

Jinja2 `trim_blocks`/`lstrip_blocks` eats newlines between
  conditional and adjacent lines

## Root Cause

With both options enabled, `{% if tags %}...{% endif %}` on one line followed by `source:` on the next produces `tags: [x]source:` (no newline).

## Resolution

1. use `{%- endif -%}` dash syntax or `{% if tags -%}` to control whitespace explicitly

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Jinja2 `trim_blocks`/`lstrip_blocks` eats newlines between
  conditional and adjacent lines
