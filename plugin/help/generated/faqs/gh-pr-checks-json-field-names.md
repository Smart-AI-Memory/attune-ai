---
type: faq
name: gh-pr-checks-json-field-names
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about gh pr checks --json field names?

## Answer

the field is `bucket` (pass/fail/pending/skipping/cancel), not `conclusion`. Full field list is exposed by passing an invalid field name and reading the error message.

**How to fix:**
- Useful for scripted pre-merge checks

```
 (pass/fail/pending/skipping/cancel), not
```

## Related Topics
- **Error**: Detailed error: `gh pr checks --json` field names
