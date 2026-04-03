---
type: error
name: read-source-before-writing-tests-for-tricky-logic
confidence: Verified
tags: [testing]
source: .claude/CLAUDE.md
---

# Error: Read source before writing tests for tricky logic

## Signature

Read source before writing tests for tricky logic

## Root Cause

The inline- comment check in `is_in_docstring_or_comment()` uses a ternary that defaults to `True` for any line not containing `eval`. Tests written against assumed behavior (expected `False`) failed. Always read the actual implementation before asserting expected values for non-obvious control flow.

## Resolution

1. Always read the actual implementation before asserting expected values for non-obvious control flow

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Read source before writing tests for tricky logic
- Task: Update test mocks and assertions
