---
type: faq
name: anchor-tag-buttons-need-text-white-no-underline
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about anchor-tag buttons need !text-white no-underline?

## Answer

The existing lesson about `text-white` being overridden on `gradient-primary` sections also applies to plain `<a>` elements styled as primary buttons (e.g., hero CTAs with `bg-[var(--primary)]`). Global styles set the link color to the primary blue and add an underline, producing invisible blue-on-blue text.

**How to fix:**
- Use `!text-white no-underline` on anchor-styled buttons, even outside gradient sections

```
text-white
```

## Related Topics
- **Error**: Detailed error: Anchor-tag buttons need `!text-white no-underline`
