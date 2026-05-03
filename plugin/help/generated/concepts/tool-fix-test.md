---
name: tool-fix-test
source: plugin/skills/fix-test/SKILL.md
summary: Fix Test is an automated diagnostic tool that identifies and fixes common
  test failures—including import errors, mock mismatches, assertion drift, and type
  errors—by classifying the root cause and applying targeted repairs with automatic
  retry and verification.
tags:
- testing
- debugging
- fixes
type: concept
---

# Fix Test

## What

Fix Test auto-diagnoses failing tests by classifying the root cause and applying targeted fixes. It recognizes four main failure categories — import errors, mock mismatches, assertion drift, and type errors — then retries up to three times, re-running the test after each fix to confirm the repair succeeded.

## Why

Most test failures fall into a handful of recurring patterns: stale mock paths, renamed imports, changed return types, shifted assertion values. Manually diagnosing these is repetitive and slow. Fix Test recognizes these patterns automatically and applies the correct fix, eliminating the manual diagnosis loop.

## When to Use

- Pytest reports failures after a refactor or rename
- A dependency upgrade changed an API your tests relied on
- CI fails on tests you did not intentionally modify
- You need to batch-fix a test suite after a large migration

## What It Diagnoses

| Root Cause | Example | Fix Applied |
|---|---|---|
| Import error | Module renamed or moved | Updates the import path |
| Mock mismatch | `patch()` target is stale | Corrects the patch string |
| Assertion drift | Return value changed | Updates the expected value |
| Type error | Function signature changed | Fixes call arguments |
| Missing fixture | `conftest.py` not loaded | Adds or relocates the fixture |

## Related Topics

- **Task** — Use the Fix Test skill: step-by-step walkthrough
- **Reference** — Fix Test skill: full option and behavior reference
