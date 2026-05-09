---
type: faq
name: tags-pushed-before-squash-merge-point-to-the-wrong-commit
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about tags pushed before squash-merge point to the wrong commit?

## Answer

If you push a tag before the PR merges (e.g., `git push origin v5.8.0`), the tag points to the pre-squash commit on the feature branch. After squash-merge, the main branch has a different commit hash.

```
git push origin v5.8.0
```

## Related Topics
- **Error**: Detailed error: Tags pushed before squash-merge point to the wrong commit
