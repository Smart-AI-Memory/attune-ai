---
name: smart-test
description: Run tests affected by recent changes
category: shortcut
aliases: [st]
tags: [testing, smart, selective]
version: "1.0.0"
---

# smart-test

Run only the tests affected by your recent code changes.
Faster feedback than the full suite.

## Context (pre-computed)

```bash
git diff --name-only HEAD 2>/dev/null
git diff --name-only --cached 2>/dev/null
git ls-files --others --exclude-standard '*.py' 2>/dev/null
```

## Instructions

1. Collect all changed Python files from the context above
   (staged, unstaged, and untracked `.py` files)

2. Map each file to its test counterpart:

   - Source files: `src/attune/foo/bar.py`
     → `tests/unit/foo/test_bar.py`
   - Source files: `src/attune/foo.py`
     → `tests/unit/test_foo.py`
   - Test files: include directly (already a test)
   - Non-Python files: skip silently

3. Filter to only test files that actually exist on disk

4. If no test files found:

   - If no files changed: report "No changed files
     detected" and offer to run the full suite
   - If files changed but no matching tests: report
     which source files have no tests and offer to
     generate them with `/testing generate`

5. Run the matched tests:

   ```bash
   uv run pytest <test_files> -x -q --tb=short
   ```

6. Report results:

   ```
   Smart Test Results
   ──────────────────
   Changed files: N
   Test files run: M
   Passed: X | Failed: Y | Skipped: Z
   Time: Xs (full suite estimate: ~10min)
   ```

7. If the user passed `--fix` as an argument and there
   are failures, invoke `/fix-test` with the failing
   test paths

## Examples

- `/smart-test` — run tests for all changed files
- `/smart-test --fix` — run tests, auto-fix failures
