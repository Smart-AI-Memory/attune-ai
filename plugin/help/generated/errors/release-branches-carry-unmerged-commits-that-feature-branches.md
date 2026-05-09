---
type: error
name: release-branches-carry-unmerged-commits-that-feature-branches
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Release branches carry unmerged commits that feature
  branches may depend on

## Signature

Release branches carry unmerged commits that feature
  branches may depend on

## Root Cause

`release/v5.10.0` had 8 commits not yet on `origin/main`, including `1ffc8457 feat: extract attune-author package`. Branching a new feature off `main` would have erased `packages/attune-author/` — a dependency of the new plugin work. Before branching for post-release feature work, always `git log origin/main..<release-branch>` to see whether the release branch is the effective trunk. If it is, branch from the release branch, not main.

## Resolution

1. `release/v5.10.0` had 8 commits not yet on `origin/main`, including `1ffc8457 feat: extract attune-author package`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Release branches carry unmerged commits that feature
  branches may depend on
