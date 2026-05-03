---
name: skill-descriptions-must-be-under-250-characters
source: .claude/CLAUDE.md
summary: This template explains why skill descriptions must not exceed 250 characters
  and provides a simple method to verify and fix descriptions that are too long.
tags:
- claude-code
type: faq
---

# FAQ: Why must skill descriptions be under 250 characters?

## Answer

Anthropic truncates skill descriptions that exceed 250 characters, which breaks auto-triggering from natural language inputs. During one migration, 7 of 11 skills exceeded this limit — making this a common and easy-to-miss issue.

**How to fix:**

After editing the `SKILL.md` frontmatter, verify your description length using Python:

```python
len(description)
```

If the result exceeds 250, shorten the description before saving.

## Related Topics
- **Error**: `Skill descriptions must be under 250 characters`
