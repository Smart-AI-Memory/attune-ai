---
type: error
name: enforce-admins-required-reviews-blocks-solo-dev-merges
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `enforce_admins` + required reviews blocks solo-dev merges

## Signature

`enforce_admins` + required reviews blocks solo-dev merges

## Root Cause

With `enforce_admins: true` and `required_approving_review_count: 1`, the repo owner cannot self-approve PRs (`Review Can not approve your own pull request`) and `--admin` merge also fails. The auto-approve workflow's `GITHUB_TOKEN` also can't approve the PR author's own PRs. For solo-dev repos: temporarily remove the review requirement via API, merge, then re-enable. The auto-approve workflow works correctly for PRs opened by other actors (Dependabot, collaborators).

## Resolution

1. With `enforce_admins: true` and `required_approving_review_count: 1`, the repo owner cannot self-approve PRs (`Review Can not approve your own pull request`) and `--admin` merge also fails

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
