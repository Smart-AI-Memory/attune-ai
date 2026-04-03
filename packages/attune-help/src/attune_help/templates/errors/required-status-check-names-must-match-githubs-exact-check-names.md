---
type: error
name: required-status-check-names-must-match-githubs-exact-check-names
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: Required status check names must match GitHub's exact check
  names

## Signature

Required status check names must match GitHub's exact check
  names

## Root Cause

We set `Analyze Python` as a required check, but the actual name is `Analyze (python)` (with parentheses). Mismatched names silently block merges because the expected check never appears. Always run `gh pr checks <PR>` first to see the exact check names before adding them to branch protection.

## Resolution

1. Always run `gh pr checks <PR>` first to see the exact check names before adding them to branch protection

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Required status check names must match GitHub's exact check
  names
- Tip: Best practice: Required status check names must match GitHub's exact check
  names
