---
type: warning
name: yaml-run-values-with-colons-cause-parse-errors
confidence: Verified
tags: [ci]
source: .claude/CLAUDE.md
---

# Warning: YAML `run:` values with colons cause parse errors

## Condition

A GitHub Actions `run:` like `run: gh pr review --body "Auto-approved: update"` fails YAML parsing because the colon after "Auto-approved" is interpreted as a mapping

## Risk

A GitHub Actions `run:` like `run: gh pr review --body "Auto-approved: update"` fails YAML parsing because the colon after "Auto-approved" is interpreted as a mapping

## Mitigation

1. Remove the colon or quote the entire value

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: YAML `run:` values with colons cause parse errors
