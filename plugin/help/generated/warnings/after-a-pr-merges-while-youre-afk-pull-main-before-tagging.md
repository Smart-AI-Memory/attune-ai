---
type: warning
name: after-a-pr-merges-while-youre-afk-pull-main-before-tagging
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: After a PR merges while you're AFK, pull main before
  tagging

## Condition

When a background wakeup fires and finds a PR merged, the local checkout of `main` is still behind `origin/main`

## Risk

This pairs with the existing "Tags pushed before squash- merge point to the wrong commit" lesson — same class of bug, opposite direction in time

## Mitigation

1. Always `git fetch origin && git checkout main && git pull --ff-only origin main` before `git tag -a -s v<X>`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: After a PR merges while you're AFK, pull main before
  tagging
