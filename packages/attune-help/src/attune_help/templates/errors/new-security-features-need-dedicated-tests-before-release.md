---
type: error
name: new-security-features-need-dedicated-tests-before-release
confidence: Verified
tags: [testing, security, imports, packaging]
source: .claude/CLAUDE.md
---

# Error: New security features need dedicated tests before release

## Signature

New security features need dedicated tests before release

## Root Cause

v5.0.1 shipped with 4 new security controls (rate limiter, ownership checks, module prefix restriction, workspace isolation) — all with zero effective test coverage despite 15,555 tests passing. The deep review caught this after publishing to PyPI. Run `/deep-review` on changed files BEFORE `/release prep`, not after.

## Resolution

1. Run `/deep-review` on changed files BEFORE `/release prep`, not after

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
