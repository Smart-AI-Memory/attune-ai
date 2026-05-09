---
type: error
name: gh-repo-create-source-path-push-is-a-one-shot-for-new-sibling
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `gh repo create --source <path> --push` is a one-shot
  for new sibling repos

## Signature

`gh repo create --source <path> --push` is a one-shot
  for new sibling repos

## Root Cause

Creates the GitHub repo, adds it as `origin` remote in the local path, and pushes HEAD in a single command. Flags to use: `--public --description "..." --homepage "..." --source <path> --remote origin --push`. Saves 4 separate steps (repo create → remote add → set-upstream → push) when spinning up a new workspace-sibling package.

## Resolution

1. Creates the GitHub repo, adds it as `origin` remote in the local path, and pushes HEAD in a single command

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `gh repo create --source <path> --push` is a one-shot
  for new sibling repos
