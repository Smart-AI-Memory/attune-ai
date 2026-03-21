---
name: fix-test
description: Auto-diagnose and fix failing tests
category: shortcut
aliases: [ft]
tags: [testing, fix, auto-repair]
version: "1.0.0"
---

# fix-test

Diagnose failing tests, apply fixes, and re-run — up to 3
retry attempts.

## Instructions

1. **Determine target tests**

   - If a path argument is provided, use it
   - If `--lf` or "last failed" is specified, use
     `uv run pytest --lf --no-header -q` to find them
   - If no argument, ask: "Which tests are failing?"

2. **Run the failing tests with verbose output**

   ```bash
   uv run pytest <path> -v --tb=long 2>&1
   ```

3. **Parse the failure output** for each failing test:

   - Identify the error type (AssertionError,
     ImportError, AttributeError, TypeError, etc.)
   - Extract the failing assertion or traceback
   - Note the test file path and line number

4. **Read context** for each failure:

   - Read the failing test file
   - Read the source file under test (derive from import
     statements or the test file path)

5. **Diagnose root cause** — common categories:

   | Category | Signals |
   | -------- | ------- |
   | Mock mismatch | `AttributeError` on patched name, import path changed |
   | Assertion drift | `AssertionError`, source behavior changed |
   | Missing fixture | `fixture not found`, new param needed |
   | Stale test | Tests deleted/renamed code |
   | Import error | `ModuleNotFoundError`, `ImportError` |
   | Type mismatch | `TypeError`, wrong arg count or type |

6. **Apply the fix:**

   - **Test is wrong** → fix the test (update mock path,
     assertion value, fixture usage)
   - **Source has a bug** → show the diff and ask the
     user before applying source changes
   - **Test is obsolete** → add `@pytest.mark.skip`
     with a reason string, do NOT delete the test

7. **Re-run the test** to verify the fix:

   ```bash
   uv run pytest <fixed_test> -v --tb=short
   ```

8. **If still failing**, repeat steps 3-7 (max 3 total
   attempts per test)

9. **Report summary:**

   ```
   Fix-Test Results
   ────────────────
   Tests examined: N
   Fixed: X (re-ran successfully)
   Still failing: Y (after 3 attempts)
   Skipped: Z (marked for manual review)
   ```

## Safety Rules

- **Never delete test files** — fix or skip them
- **Always show diffs** before applying source changes
- **Ask before changing source behavior** — if a fix
  would alter how production code works, confirm with
  the user first
- **Preserve test intent** — when updating assertions,
  verify the new expected value is correct, not just
  "whatever the code returns"
- **Log each attempt** — report what was tried so the
  user can review the reasoning

## Examples

- `/fix-test tests/unit/test_config.py` — fix specific
  test file
- `/fix-test --lf` — fix last failed tests
- `/fix-test tests/unit/workflows/` — fix all failures
  in a directory
