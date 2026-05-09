---
type: faq
name: release-branches-carry-unmerged-commits-that-feature-branches
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about release branches carry unmerged commits that feature branches may depend on?

## Answer

`release/v5.10.0` had 8 commits not yet on `origin/main`, including `1ffc8457 feat: extract attune-author package`. Branching a new feature off `main` would have erased `packages/attune-author/` — a dependency of the new plugin work.

```
release/v5.10.0
```

## Related Topics
- **Error**: Detailed error: Release branches carry unmerged commits that feature
  branches may depend on
