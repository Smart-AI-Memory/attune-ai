---
type: faq
name: modeltier-has-two-copies-imports-must-match
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about modelTier has two copies — imports must match?

## Answer

The enum `ModelTier` exists in both `attune.models` and `attune.workflows.base` as separate classes (`id()` differs). Tests comparing `tier_map` values will fail if the import source doesn't match the workflow's import.

**How to fix:**
- Check which module the workflow imports from and use the same one in tests

```
 exists in both
```

## Related Topics
- **Error**: Detailed error: `ModelTier` has two copies — imports must match
