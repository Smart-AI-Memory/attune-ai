---
type: warning
name: text-white-on-gradient-primary-sections-gets-overridden
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Warning: `text-white` on `gradient-primary` sections gets overridden

## Condition

Tailwind's `text-white` class is overridden by global styles on sections using `gradient-primary`

## Risk

Ignoring this guidance may cause: `text-white` on `gradient-primary` sections gets overridden

## Mitigation

1. Use `!text-white` (Tailwind's `!important` modifier) to force white text
2. Use inline Tailwind classes instead: `px-8 py-4 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `text-white` on `gradient-primary` sections gets overridden
