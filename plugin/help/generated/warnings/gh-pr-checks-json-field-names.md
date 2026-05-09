---
type: warning
name: gh-pr-checks-json-field-names
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: `gh pr checks --json` field names

## Condition

the field is `bucket` (pass/fail/pending/skipping/cancel), not `conclusion`

## Risk

the field is `bucket` (pass/fail/pending/skipping/cancel), not `conclusion`

## Mitigation

1. Useful for scripted pre-merge checks

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `gh pr checks --json` field names
