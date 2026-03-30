---
type: faq
name: broad-gitignore-patterns-match-nested-directories
tags: [claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Broad gitignore patterns match nested directories?

## Answer

A root `.gitignore` entry `planning/` (without leading `/`) matches `plugin/skills/planning/` too. Scope patterns with `/planning/` for root-only, and add `!plugin/skills/planning/` exceptions when needed.

```
.gitignore
```

## Related Topics
- **Error**: Detailed error: Broad gitignore patterns match nested directories
