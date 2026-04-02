---
type: concept
name: tool-fix-test
tags: [testing, debugging, fixes]
source: plugin/skills/fix-test/SKILL.md
---

# Fix Test

## What

Auto-diagnoses failing tests by classifying the root cause
(import errors, mock mismatches, assertion drift, type
errors) and applies targeted fixes. Retries up to 3 times,
re-running the test after each fix to confirm the repair
actually works.

## Why

Most test failures fall into a handful of categories --
stale mock paths, renamed imports, changed return types.
Fix-test recognizes these patterns and applies the right
fix automatically, saving you the manual diagnosis loop.

## When to use

- When pytest shows failures after a refactor or rename
- After upgrading a dependency that changed an API
- When CI fails on tests you did not intentionally change
- To batch-fix test suites after a large migration

## What it diagnoses

| Root cause | Example | Fix applied |
|------------|---------|-------------|
| Import error | Module renamed or moved | Updates import path |
| Mock mismatch | `patch()` target stale | Fixes patch string |
| Assertion drift | Return value changed | Updates expected value |
| Type error | Signature changed | Fixes call arguments |
| Fixture missing | conftest not loaded | Adds or moves fixture |

## Related Topics

- **Task**: Use the fix-test skill -- step-by-step
- **Reference**: Skill: fix-test -- full reference
