---
type: faq
name: stop-hooks-inject-stderr-not-stdout
tags: [claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Stop hooks inject stderr, not stdout?

## Answer

Claude Code's Stop hook with exit code 2 surfaces the hook's **stderr** as the feedback message.


**Fix:**

- Use `print(..., file=sys.stderr)` — `print()` writes to stdout which is silently discarded

```
print(..., file=sys.stderr)
```

## Related Topics
- **Error**: Detailed error: Stop hooks inject stderr, not stdout
