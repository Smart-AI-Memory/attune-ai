---
type: warning
name: read-source-before-writing-tests-for-tricky-logic
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Warning: Read source before writing tests for tricky logic

## Condition

The inline- comment check in `is_in_docstring_or_comment()` uses a ternary that defaults to `True` for any line not containing `eval`

## Risk

Tests written against assumed behavior (expected `False`) failed

## Mitigation

1. Always read the actual implementation before asserting expected values for non-obvious control flow

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Read source before writing tests for tricky logic
