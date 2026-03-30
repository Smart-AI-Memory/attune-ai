---
type: faq
name: claude-plugin-install-is-marketplace-only
tags: [testing, claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: `claude plugin install` is marketplace-only?

## Answer

The `install` command does not accept local paths. For local testing use `claude --plugin-dir ./plugin`.

```
 command does not accept local paths. For local testing use
```

## Related Topics
- **Error**: Detailed error: `claude plugin install` is marketplace-only
