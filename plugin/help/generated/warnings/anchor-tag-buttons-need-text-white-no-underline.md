---
type: warning
name: anchor-tag-buttons-need-text-white-no-underline
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Anchor-tag buttons need `!text-white no-underline`

## Condition

The existing lesson about `text-white` being overridden on `gradient-primary` sections also applies to plain `<a>` elements styled as primary buttons (e.g., hero CTAs with `bg-[var(--primary)]`)

## Risk

Ignoring this guidance may cause: Anchor-tag buttons need `!text-white no-underline`

## Mitigation

1. Use `!text-white no-underline` on anchor-styled buttons, even outside gradient sections

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Anchor-tag buttons need `!text-white no-underline`
