---
type: error
name: squash-merge-deletes-the-remote-branch-subsequent-push-silently
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached

## Signature

Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached

## Root Cause

After a squash merge, GitHub deletes the feature branch. If you push more commits to the same branch name later, `git push` succeeds with `* [new branch]` output — GitHub recreates the branch but there's no PR attached. Commits are orphaned on a branch no one watches. Always check `gh pr view <n> --json state` before adding more commits to a branch — if state is `MERGED`, rebase onto `origin/main` and open a new PR instead of pushing to the stale branch.

## Resolution

1. Always check `gh pr view <n> --json state` before adding more commits to a branch — if state is `MERGED`, rebase onto `origin/main` and open a new PR instead of pushing to the stale branch

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached
