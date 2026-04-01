---
type: faq
name: stop-hooks-loop-without-a-sentinel
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about stop hooks loop without a sentinel?

## Answer

Exit code 2 blocks one stop attempt but the next attempt triggers the hook again, creating an infinite loop.

**How to fix:**
- Use a TTL sentinel file (`~/.attune/lessons_reminded`) to fire the reminder only once per session

```
~/.attune/lessons_reminded
```

## Related Topics
- **Error**: Detailed error: Stop hooks loop without a sentinel
