---
type: faq
name: dry-run-candidate-golden-queries-through-the-resolver-before
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about dry-run candidate golden queries through the resolver before assigning difficulty labels?

## Answer

when expanding a golden-query fixture, every candidate query should pass through `resolve_topic()` (or the equivalent) first. Labels based on guessing — "this medium query probably resolves because the tag exists" — hide real corpus gaps and produce mislabeled fixtures.

```
resolve_topic()
```

## Related Topics
- **Error**: Detailed error: Dry-run candidate golden queries through the
  resolver before assigning difficulty labels
