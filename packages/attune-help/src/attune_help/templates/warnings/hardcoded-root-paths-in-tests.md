---
type: warning
name: hardcoded-root-paths-in-tests
confidence: Verified
tags: [ci, testing]
source: .claude/CLAUDE.md
---

# Warning: Hardcoded `/root/` paths in tests

## Condition

Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error

## Risk

Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error

## Mitigation

1. Avoid `/root/` in test fixtures — CI runners often execute as root, making the path accessible and triggering real I/O instead of the mocked error
2. Use `tmp_path` instead

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Hardcoded `/root/` paths in tests
