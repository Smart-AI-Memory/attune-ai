---
type: error
name: validate-infrastructure-against-user-value-before-extending
confidence: Verified
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# Error: Validate infrastructure against user value before extending

## Signature

Validate infrastructure against user value before extending

## Root Cause

BEP middleware was well-built (93 tests, clean protocol) but had zero working skills and no integration with CLI workflows — the surface where all user value lives. Always validate that new infrastructure serves actual users before investing in production hardening.

## Resolution

1. Always validate that new infrastructure serves actual users before investing in production hardening

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Validate infrastructure against user value before extending
- Task: Update test mocks and assertions
