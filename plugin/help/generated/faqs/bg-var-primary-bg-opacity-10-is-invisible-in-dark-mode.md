---
type: faq
name: bg-var-primary-bg-opacity-10-is-invisible-in-dark-mode
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode?

## Answer

A 10% opacity tint of dark blue (`#1E40AF`) on a dark background (`#0F172A`) produces near-zero contrast. This affected callout boxes and hero sections on the attune-lite page.


**Fix:**

- Use `bg-[var(--background)]` with a colored border instead, or switch to `gradient-accent` (purple) which is brighter

```
) on a dark background (
```

## Related Topics
- **Error**: Detailed error: `bg-[var(--primary)] bg-opacity-10` is invisible in dark mode
