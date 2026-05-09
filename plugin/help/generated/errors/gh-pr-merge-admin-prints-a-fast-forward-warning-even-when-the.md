---
type: error
name: gh-pr-merge-admin-prints-a-fast-forward-warning-even-when-the
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds

## Signature

`gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds

## Root Cause

After an admin-merge, the CLI attempts a local fast-forward of your local main to origin/main. If your local main diverged (e.g., you had feature-branch commits before the squash), the CLI prints `fatal: Not possible to fast-forward, aborting` and `! warning: not possible to fast-forward to: "main"`. The remote merge already succeeded — the warning is about the local refresh failing. Always verify the actual merge state via `gh pr view <n> --json state,mergedAt,mergeCommit` before assuming the command failed.

## Resolution

1. Always verify the actual merge state via `gh pr view <n> --json state,mergedAt,mergeCommit` before assuming the command failed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds
