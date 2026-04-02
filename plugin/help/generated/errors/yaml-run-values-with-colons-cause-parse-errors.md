---
type: error
name: yaml-run-values-with-colons-cause-parse-errors
confidence: Verified
tags: [ci]
source: .claude/CLAUDE.md
---

# Error: YAML `run:` values with colons cause parse errors

## Signature

` fails YAML parsing because the colon after

## Root Cause

A GitHub Actions `run:` like `run: gh pr review --body "Auto-approved: update"` fails YAML parsing because the colon after "Auto-approved" is interpreted as a mapping. Remove the colon or quote the entire value.

## Resolution

1. Remove the colon or quote the entire value

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: YAML `run:` values with colons cause parse errors
