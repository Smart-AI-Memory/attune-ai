---
type: error
name: gh-pr-merge-admin-is-blocked-by-in-progress-required-checks
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: `gh pr merge --admin` is blocked by in-progress required
  checks

## Signature

`gh pr merge --admin` is blocked by in-progress required
  checks

## Root Cause

The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running. GitHub returns `Required status check "X" is in progress`. You must wait for required checks to complete (or cancel them) before even an admin merge is possible. Budget extra time when the test matrix is large (12 platform combos ~15 min).

## Resolution

1. The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
