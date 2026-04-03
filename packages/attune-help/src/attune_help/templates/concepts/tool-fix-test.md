---
type: concept
name: tool-fix-test
tags: [testing, debugging, fixes]
source: plugin/skills/fix-test/SKILL.md
---

# Fix Test

Fix-test auto-diagnoses failing tests by classifying the
root cause and applying a targeted fix. It re-runs the
test after each repair attempt and retries up to 3 times,
so by the end you either have a passing test or a clear
explanation of what still needs manual attention.

## What root causes it handles

| Root cause | What went wrong | Auto-fixable? |
|------------|-----------------|---------------|
| **Import error** | Module renamed, moved, or deleted | Yes |
| **Mock mismatch** | `patch()` target is stale after refactor | Yes |
| **Assertion drift** | Return value or output changed | Yes |
| **Type error** | Function signature changed | Yes |
| **Fixture missing** | conftest not loaded or fixture renamed | Usually |
| **Environment issue** | Missing env var, wrong Python version | Sometimes |

## When you'd use it

Run fix-test when pytest shows failures after a refactor,
after upgrading a dependency that changed an API, when CI
breaks on tests you didn't intentionally change, or to
batch-repair a test suite after a large migration. It
handles the tedious "read traceback, identify cause, edit
test, re-run" loop automatically.

## What to expect

When you say "fix the failing test," here is the flow:

1. **Scoping** -- you're asked which test is failing and
   whether it broke recently. Providing the test name
   inline (e.g., "fix test_auth.py") skips the questions.
2. **Diagnosis** -- the failing test is run, the traceback
   is classified into a root cause category, and a fix is
   proposed.
3. **Repair + retry** -- the fix is applied and the test
   is re-run. If it still fails, the new error is
   diagnosed and another fix is attempted (up to 3 total).
4. **Report** -- you see which tests were fixed, which
   still fail, how many attempts were used, and what to
   try next.

The skill runs on your Claude subscription -- no API key
or additional budget needed.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is smart-test?"** to generate new tests
  instead of fixing broken ones
- Say **"tell me about code quality"** for broader code
  review
