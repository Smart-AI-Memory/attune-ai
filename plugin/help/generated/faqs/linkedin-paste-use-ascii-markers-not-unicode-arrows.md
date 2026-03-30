---
type: faq
name: linkedin-paste-use-ascii-markers-not-unicode-arrows
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: LinkedIn paste: use ASCII markers, not Unicode arrows?

## Answer

Unicode characters like `▶`/`◀` used as code-block delimiters get misinterpreted by LinkedIn's editor, causing content duplication and markers leaking into code blocks.


**Fix:**

- Use plain ASCII like `--- CODE START ---` / `--- CODE END ---` instead

```
--- CODE START ---
```

## Related Topics
- **Error**: Detailed error: LinkedIn paste: use ASCII markers, not Unicode arrows
