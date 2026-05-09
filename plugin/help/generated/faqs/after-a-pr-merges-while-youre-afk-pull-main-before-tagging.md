---
type: faq
name: after-a-pr-merges-while-youre-afk-pull-main-before-tagging
tags: [git]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about after a PR merges while you're AFK, pull main before tagging?

## Answer

When a background wakeup fires and finds a PR merged, the local checkout of `main` is still behind `origin/main`. If you tag without syncing first, you tag the old commit (before the squash), which means the tag won't anchor to the release content.

**How to fix:**
- Always `git fetch origin && git checkout main && git pull --ff-only origin main` before `git tag -a -s v<X>`

```
 is still behind
```

## Related Topics
- **Error**: Detailed error: After a PR merges while you're AFK, pull main before
  tagging
