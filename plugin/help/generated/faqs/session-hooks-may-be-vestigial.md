---
type: faq
name: session-hooks-may-be-vestigial
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about session hooks may be vestigial?

## Answer

`session_end.py` saves near-empty shells (zero tokens, no patterns detected). Verify they are wired to collect meaningful data before building on top of them or advertising session memory as a feature.

```
session_end.py
```

## Related Topics
- **Error**: Detailed error: Session hooks may be vestigial
