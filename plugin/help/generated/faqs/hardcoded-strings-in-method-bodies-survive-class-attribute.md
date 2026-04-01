---
type: faq
name: hardcoded-strings-in-method-bodies-survive-class-attribute
source: .claude/CLAUDE.md
---

# FAQ: What should I know about hardcoded strings in method bodies survive class attribute renames?

## Answer

Changing `name = "deep-review-sdk"` to `"deep-review"` on the class didn't fix a hardcoded `"workflow": "deep-review-sdk"` string inside `execute()`. After renaming a class attribute, always grep for the old value across the entire source file to catch hardcoded duplicates in method bodies and metadata dicts.

```
name = "deep-review-sdk"
```

## Related Topics
- **Error**: Detailed error: Hardcoded strings in method bodies survive class attribute
  renames
