---
type: faq
name: next-js-shared-data-libs-prevent-page-duplication
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about next.js shared data libs prevent page duplication?

## Answer

When multiple pages need the same data array (e.g. wizard list), extract it to `lib/<name>.ts` and import from there.

```
lib/<name>.ts
```

## Related Topics
- **Error**: Detailed error: Next.js shared data libs prevent page duplication
