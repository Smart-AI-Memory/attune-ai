---
type: faq
name: codeql-alerts-dismissible-in-bulk-via-gh-api
tags: [testing]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about codeQL alerts dismissible in bulk via gh api?

## Answer

Valid reasons: `false positive`, `won't fix`, `used in tests`.

**How to fix:**
- Use `gh api repos/OWNER/REPO/code-scanning/alerts/ID -X PATCH -f state=dismissed -f dismissed_reason="false positive" -f dismissed_comment="..."` to batch-dismiss with documented reasons

```
 to batch-dismiss with documented reasons. Valid reasons:
```

## Related Topics
- **Error**: Detailed error: CodeQL alerts dismissible in bulk via `gh api`
