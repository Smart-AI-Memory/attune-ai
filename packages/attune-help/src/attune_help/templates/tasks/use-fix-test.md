---
type: task
name: use-fix-test
tags: [testing, skill, task]
source: plugin/skills/fix-test/SKILL.md
---

# How to Fix a Failing Test

## Quick start

The fastest way: just say what's broken.

```
fix tests/unit/test_auth.py
```

Or use the skill directly:

```
/fix-test tests/unit/test_auth.py::test_login_expired
```

If you name the test inline, the skill skips all
questions and jumps straight to diagnosis.

## Guided flow

If you don't specify a target, the skill asks two
questions before running:

1. **Which test?** -- "Which test is failing? A file,
   a test name, or should I find failures automatically?"
2. **When did it break?** -- "Did this start failing
   after a recent change, or has it been broken a while?"

Your answers help narrow the diagnosis. If the failure
started after a rename, the skill prioritizes import
errors and mock mismatches. If it's been broken a while,
it checks for environment issues and fixture drift.

## Reading the diagnosis

After running the test, you'll see something like this:

```
Diagnosis

Test:       test_login_expired
Error:      AttributeError: module 'auth' has no
            attribute 'SessionManager'
Root cause: Import error -- SessionManager was renamed
            to AuthSession in commit abc1234
Fix:        Update import in test_auth.py line 12

Applying fix... re-running test...

  PASSED  test_login_expired (attempt 1/3)
```

The diagnosis identifies the root cause category, explains
what changed, and shows exactly what was fixed.

## The retry cycle

If the first fix doesn't work, the skill re-reads the new
traceback and tries again:

```
Attempt 1/3: Fixed import path -- still failing
Attempt 2/3: Fixed mock target to match new import
  PASSED  test_login_expired (attempt 2/3)
```

Up to 3 attempts total. Each attempt diagnoses fresh from
the latest error, so cascading issues (e.g., a rename that
breaks both the import and the mock) get resolved in
sequence.

## When it can't fix automatically

If all 3 attempts are exhausted, you get a clear summary
of what was tried and what remains:

```
Fix Test Results

Tests Fixed: 3/4 | Attempts Used: 3/3

Still Failing
  test_complex_flow -- Requires manual refactor:
  test logic depends on removed database fixture.
  Suggestion: rewrite test to use the new repository
  pattern introduced in src/auth/repository.py.
```

## What to do next

After the results, you have several options:

- **Fix more tests** -- "fix the rest of the failing
  tests in tests/unit/"
- **Generate new tests** -- "generate tests for the
  module I just refactored"
- **Check for similar breakage** -- "are there other
  tests with the same stale import?"
- **Get the full reference** -- say "tell me more" for
  root cause categories, retry behavior, and
  configuration details

## Want to learn more?

- Say **"tell me more"** for the complete reference --
  all root cause categories, fix strategies, retry
  behavior
- Say **"what is fix-test?"** to go back to the overview
- Say **"generate tests"** to create new tests with
  smart-test instead
