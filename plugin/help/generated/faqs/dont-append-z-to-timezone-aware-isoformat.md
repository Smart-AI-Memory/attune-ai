---
type: faq
name: dont-append-z-to-timezone-aware-isoformat
tags: [python]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Don't append `+ "Z"` to timezone-aware `.isoformat()`?

## Answer

`datetime.now(timezone.utc).isoformat()` already produces `2026-03-08T12:00:00+00:00`. Appending `+ "Z"` creates `+00:00Z` which, when passed through `.replace("Z", "+00:00")`, becomes the invalid `+00:00+00:00`.

```
datetime.now(timezone.utc).isoformat()
```

## Related Topics
- **Error**: Detailed error: Don't append `+ "Z"` to timezone-aware `.isoformat()`
