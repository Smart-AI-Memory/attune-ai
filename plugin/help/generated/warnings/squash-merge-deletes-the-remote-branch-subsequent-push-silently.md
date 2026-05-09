---
type: warning
name: squash-merge-deletes-the-remote-branch-subsequent-push-silently
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached

## Condition

After a squash merge, GitHub deletes the feature branch

## Risk

Ignoring this guidance may cause: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached

## Mitigation

1. Always check `gh pr view <n> --json state` before adding more commits to a branch — if state is `MERGED`, rebase onto `origin/main` and open a new PR instead of pushing to the stale branch

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Squash-merge deletes the remote branch; subsequent push
  silently recreates it with no PR attached
