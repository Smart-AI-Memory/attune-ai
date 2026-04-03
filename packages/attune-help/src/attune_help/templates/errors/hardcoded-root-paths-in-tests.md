---
type: error
name: hardcoded-root-paths-in-tests
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Error: Hardcoded `/root/` paths in tests

## Signature

Hardcoded `/root/` paths in tests

## Root Cause

Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error. Use `tmp_path` instead.

## Resolution

1. Use `tmp_path` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Hardcoded `/root/` paths in tests
- Tip: Best practice: Hardcoded `/root/` paths in tests
- Task: Update test mocks and assertions
