---
type: error
name: gh-api-x-patch-f-name-n-rejects-integers-as-strings
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Error: `gh api -X PATCH ... -f name=N` rejects integers as
  strings

## Signature

`gh api -X PATCH ... -f name=N` rejects integers as
  strings

## Root Cause

`gh api` flag `-f` always sends string values, so `-f required_approving_review_count=1` produces a 422 error `"1" is not an integer`. Use `-F` instead — it infers the type (integer, boolean, etc.) from the value. Specifically matters for `branches/<name>/protection/required_pull_request_reviews` updates during the temp-remove-review/admin-merge/restore dance.

## Resolution

1. Use `-F` instead — it infers the type (integer, boolean, etc.) from the value

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `gh api -X PATCH ... -f name=N` rejects integers as
  strings
- Task: Update test mocks and assertions
