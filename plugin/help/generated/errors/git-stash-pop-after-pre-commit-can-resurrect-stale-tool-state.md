---
type: error
name: git-stash-pop-after-pre-commit-can-resurrect-stale-tool-state
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: `git stash pop` after pre-commit can resurrect stale
  tool state

## Signature

`git stash pop` after pre-commit can resurrect stale
  tool state

## Root Cause

When pre-commit's `detect-secrets` hook bumps `.secrets.baseline`'s schema version (e.g. `1.4.0 → 1.5.0`) during a commit, a previously stashed copy of `.secrets.baseline` will conflict on `git stash pop` and revert the schema bump. After popping, always `git diff .secrets.baseline` and `git checkout .secrets.baseline` to discard any reverted changes that came from the stash.

## Resolution

1. When pre-commit's `detect-secrets` hook bumps `.secrets.baseline`'s schema version (e.g

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `git stash pop` after pre-commit can resurrect stale
  tool state
