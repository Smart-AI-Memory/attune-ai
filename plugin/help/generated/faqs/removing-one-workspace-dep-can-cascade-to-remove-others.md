---
type: faq
name: removing-one-workspace-dep-can-cascade-to-remove-others
tags: [imports, git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about removing one workspace dep can cascade to remove others?

## Answer

When `attune-ai` declared `attune-author` as a core dep, the lockfile also pulled in `attune-help` (because `attune-author` depends on it). Removing `attune-author` from `attune-ai`'s deps caused `uv lock` to drop BOTH `attune-author` AND `attune-help` from the lockfile.

**How to fix:**
- Always check the cascade with `uv lock` *before* committing, and verify that any code importing the cascaded-out package has a try/except fallback

```
 declared
```

## Related Topics
- **Error**: Detailed error: Removing one workspace dep can cascade to remove
  others
