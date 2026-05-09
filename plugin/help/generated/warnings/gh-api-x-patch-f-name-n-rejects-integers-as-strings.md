---
type: warning
name: gh-api-x-patch-f-name-n-rejects-integers-as-strings
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: `gh api -X PATCH ... -f name=N` rejects integers as
  strings

## Condition

`gh api` flag `-f` always sends string values, so `-f required_approving_review_count=1` produces a 422 error `"1" is not an integer`

## Risk

`gh api` flag `-f` always sends string values, so `-f required_approving_review_count=1` produces a 422 error `"1" is not an integer`

## Mitigation

1. Use `-F` instead — it infers the type (integer, boolean, etc.) from the value

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `gh api -X PATCH ... -f name=N` rejects integers as
  strings
