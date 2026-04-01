---
type: faq
name: datetime-utcnow-datetime-nowtimezone-utc-cascades-through-the
tags: [testing, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about datetime.utcnow() → datetime.now(timezone.utc) cascades through the entire codebase?

## Answer

Replacing `utcnow()` (naive) with `now(timezone.utc)` (aware) in source code causes `TypeError: can't compare offset-naive and offset-aware datetimes` everywhere that stored/parsed timestamps interact with the new aware values. This includes `_parse_timestamp()` helpers, `fromisoformat()` calls that strip `Z`, and test fixtures that create naive datetimes.

```
 (naive) with
```

## Related Topics
- **Error**: Detailed error: `datetime.utcnow()` → `datetime.now(timezone.utc)` cascades
  through the entire codebase
