---
type: warning
name: gh-pr-merge-admin-is-blocked-by-in-progress-required-checks
confidence: Verified
tags: [testing, git]
source: .claude/CLAUDE.md
---

# Warning: `gh pr merge --admin` is blocked by in-progress required
  checks

## Condition

The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running

## Risk

The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running

## Mitigation

1. The `--admin` flag only bypasses failed or missing checks — it cannot override checks that are still running

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `gh pr merge --admin` is blocked by in-progress required
  checks
