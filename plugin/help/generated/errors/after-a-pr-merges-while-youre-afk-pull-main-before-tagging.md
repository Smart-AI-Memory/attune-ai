---
type: error
name: after-a-pr-merges-while-youre-afk-pull-main-before-tagging
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: After a PR merges while you're AFK, pull main before
  tagging

## Signature

After a PR merges while you're AFK, pull main before
  tagging

## Root Cause

When a background wakeup fires and finds a PR merged, the local checkout of `main` is still behind `origin/main`. If you tag without syncing first, you tag the old commit (before the squash), which means the tag won't anchor to the release content. Always `git fetch origin && git checkout main && git pull --ff-only origin main` before `git tag -a -s v<X>`. Then `git tag --verify v<X>` and confirm the `object <sha>` matches `gh pr view <N> --json mergeCommit --jq .mergeCommit.oid`. This pairs with the existing "Tags pushed before squash- merge point to the wrong commit" lesson — same class of bug, opposite direction in time.

## Resolution

1. Always `git fetch origin && git checkout main && git pull --ff-only origin main` before `git tag -a -s v<X>`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: After a PR merges while you're AFK, pull main before
  tagging
