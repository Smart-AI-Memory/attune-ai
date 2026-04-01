---
type: warning
name: new-security-features-need-dedicated-tests-before-release
confidence: Verified
tags: [testing, security, imports, packaging]
source: .claude/CLAUDE.md
---

# Warning: New security features need dedicated tests before release

## Condition

v5.0.1 shipped with 4 new security controls (rate limiter, ownership checks, module prefix restriction, workspace isolation) — all with zero effective test coverage despite 15,555 tests passing

## Risk

Ignoring this guidance may cause: New security features need dedicated tests before release

## Mitigation

1. Run `/deep-review` on changed files BEFORE `/release prep`, not after

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: New security features need dedicated tests before release
