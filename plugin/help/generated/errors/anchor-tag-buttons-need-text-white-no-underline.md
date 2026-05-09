---
type: error
name: anchor-tag-buttons-need-text-white-no-underline
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Anchor-tag buttons need `!text-white no-underline`

## Signature

Anchor-tag buttons need `!text-white no-underline`

## Root Cause

The existing lesson about `text-white` being overridden on `gradient-primary` sections also applies to plain `<a>` elements styled as primary buttons (e.g., hero CTAs with `bg-[var(--primary)]`). Global styles set the link color to the primary blue and add an underline, producing invisible blue-on-blue text. Use `!text-white no-underline` on anchor-styled buttons, even outside gradient sections.

## Resolution

1. Use `!text-white no-underline` on anchor-styled buttons, even outside gradient sections

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Anchor-tag buttons need `!text-white no-underline`
