---
type: error
name: gh-pr-checks-json-field-names
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: `gh pr checks --json` field names

## Signature

`gh pr checks --json` field names

## Root Cause

the field is `bucket` (pass/fail/pending/skipping/cancel), not `conclusion`. Full field list is exposed by passing an invalid field name and reading the error message. Useful for scripted pre-merge checks.

## Resolution

1. Useful for scripted pre-merge checks

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `gh pr checks --json` field names
