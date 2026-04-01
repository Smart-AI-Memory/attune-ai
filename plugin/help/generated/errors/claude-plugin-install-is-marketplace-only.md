---
type: error
name: claude-plugin-install-is-marketplace-only
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: `claude plugin install` is marketplace-only

## Signature

`claude plugin install` is marketplace-only

## Root Cause

The `install` command does not accept local paths. For local testing use `claude --plugin-dir ./plugin`. For distribution, create a `.claude-plugin/marketplace.json` at the repo root and have users run `claude plugin marketplace add owner/repo` then `claude plugin install name@marketplace`.

## Resolution

1. The `install` command does not accept local paths

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `claude plugin install` is marketplace-only
- Task: Update test mocks and assertions
