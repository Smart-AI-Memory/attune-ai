---
type: warning
name: git-stash-pop-after-pre-commit-can-resurrect-stale-tool-state
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `git stash pop` after pre-commit can resurrect stale
  tool state

## Condition

When pre-commit's `detect-secrets` hook bumps `.secrets.baseline`'s schema version (e.g

## Risk

`1.4.0 → 1.5.0`) during a commit, a previously stashed copy of `.secrets.baseline` will conflict on `git stash pop` and revert the schema bump

## Mitigation

1. When pre-commit's `detect-secrets` hook bumps `.secrets.baseline`'s schema version (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `git stash pop` after pre-commit can resurrect stale
  tool state
