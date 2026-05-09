---
type: warning
name: gh-pr-merge-admin-prints-a-fast-forward-warning-even-when-the
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: `gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds

## Condition

After an admin-merge, the CLI attempts a local fast-forward of your local main to origin/main

## Risk

The remote merge already succeeded — the warning is about the local refresh failing

## Mitigation

1. Always verify the actual merge state via `gh pr view <n> --json state,mergedAt,mergeCommit` before assuming the command failed

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `gh pr merge --admin` prints a fast-forward warning even
  when the remote merge succeeds
