---
type: faq
name: skill-descriptions-must-be-under-250-characters
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about skill descriptions must be under 250 characters?

## Answer

Anthropic truncates skill descriptions longer than 250 chars, which breaks auto-triggering from natural language. Our initial migration had 7 of 11 skills over the limit.

**How to fix:**
- Always check with `len(description)` after editing SKILL.md frontmatter

```
len(description)
```

## Related Topics
- **Error**: Detailed error: Skill descriptions must be under 250 characters
