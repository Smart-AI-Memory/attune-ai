---
type: faq
name: required-status-check-names-must-match-githubs-exact-check-names
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about required status check names must match GitHub's exact check names?

## Answer

We set `Analyze Python` as a required check, but the actual name is `Analyze (python)` (with parentheses). Mismatched names silently block merges because the expected check never appears.

**How to fix:**
- Always run `gh pr checks <PR>` first to see the exact check names before adding them to branch protection

```
Analyze Python
```

## Related Topics
- **Error**: Detailed error: Required status check names must match GitHub's exact check
  names
