---
type: error
name: text-white-on-gradient-primary-sections-gets-overridden
confidence: Verified
tags: [imports]
source: .claude/CLAUDE.md
---

# Error: `text-white` on `gradient-primary` sections gets overridden

## Signature

`text-white` on `gradient-primary` sections gets overridden

## Root Cause

Tailwind's `text-white` class is overridden by global styles on sections using `gradient-primary`. Use `!text-white` (Tailwind's `!important` modifier) to force white text. Similarly, `btn-outline-white` and `btn-secondary` don't exist in `globals.css` — buttons using them are invisible. Use inline Tailwind classes instead: `px-8 py-4 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors`.

## Resolution

1. Use `!text-white` (Tailwind's `!important` modifier) to force white text
2. Use inline Tailwind classes instead: `px-8 py-4 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: `text-white` on `gradient-primary` sections gets overridden
- Tip: Best practice: `text-white` on `gradient-primary` sections gets overridden
