---
type: warning
name: validate-infrastructure-against-user-value-before-extending
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Validate infrastructure against user value before extending

## Condition

BEP middleware was well-built (93 tests, clean protocol) but had zero working skills and no integration with CLI workflows — the surface where all user value lives

## Risk

Ignoring this guidance may cause: Validate infrastructure against user value before extending

## Mitigation

1. Always validate that new infrastructure serves actual users before investing in production hardening

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Validate infrastructure against user value before extending
