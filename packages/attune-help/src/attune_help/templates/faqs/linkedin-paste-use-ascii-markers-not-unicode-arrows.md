---
type: faq
name: linkedin-paste-use-ascii-markers-not-unicode-arrows
source: .claude/CLAUDE.md
---

# FAQ: What should I know about linkedIn paste: use ASCII markers, not Unicode arrows?

## Answer

Unicode characters like `▶`/`◀` used as code-block delimiters get misinterpreted by LinkedIn's editor, causing content duplication and markers leaking into code blocks.

**How to fix:**
- Use plain ASCII like `--- CODE START ---` / `--- CODE END ---` instead

```
--- CODE START ---
```

## Related Topics
- **Error**: Detailed error: LinkedIn paste: use ASCII markers, not Unicode arrows
