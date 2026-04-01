---
type: faq
name: list-workflows-deduplication-must-keep-base-names-visible
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about list_workflows() deduplication must keep base names visible?

## Answer

When hiding SDK duplicates, only skip entries in `_SDK_REVERSE_MAP` (the explicit `-sdk` suffixed names). Do NOT also skip base names that have an SDK variant — those are the names users see and type.

```
_SDK_REVERSE_MAP
```

## Related Topics
- **Error**: Detailed error: `list_workflows()` deduplication must keep base names visible
