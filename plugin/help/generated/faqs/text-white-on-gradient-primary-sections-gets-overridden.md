---
type: faq
name: text-white-on-gradient-primary-sections-gets-overridden
tags: [imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about text-white on gradient-primary sections gets overridden?

## Answer

Tailwind's `text-white` class is overridden by global styles on sections using `gradient-primary`. Similarly, `btn-outline-white` and `btn-secondary` don't exist in `globals.css` — buttons using them are invisible.

**How to fix:**
- Use `!text-white` (Tailwind's `!important` modifier) to force white text
- Use inline Tailwind classes instead: `px-8 py-4 rounded-lg font-medium !text-white border-2 border-white/60 hover:bg-white/15 transition-colors`

```
text-white
```

## Related Topics
- **Error**: Detailed error: `text-white` on `gradient-primary` sections gets overridden
