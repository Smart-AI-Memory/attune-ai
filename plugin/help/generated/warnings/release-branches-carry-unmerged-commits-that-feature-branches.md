---
type: warning
name: release-branches-carry-unmerged-commits-that-feature-branches
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Release branches carry unmerged commits that feature
  branches may depend on

## Condition

`release/v5.10.0` had 8 commits not yet on `origin/main`, including `1ffc8457 feat: extract attune-author package`

## Risk

Ignoring this guidance may cause: Release branches carry unmerged commits that feature
  branches may depend on

## Mitigation

1. Before branching for post-release feature work, always `git log origin/main..<release-branch>` to see whether the release branch is the effective trunk

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Release branches carry unmerged commits that feature
  branches may depend on
