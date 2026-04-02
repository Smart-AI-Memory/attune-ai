---
type: warning
name: required-status-check-names-must-match-githubs-exact-check-names
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: Required status check names must match GitHub's exact check
  names

## Condition

We set `Analyze Python` as a required check, but the actual name is `Analyze (python)` (with parentheses)

## Risk

Mismatched names silently block merges because the expected check never appears

## Mitigation

1. Always run `gh pr checks <PR>` first to see the exact check names before adding them to branch protection

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Required status check names must match GitHub's exact check
  names
