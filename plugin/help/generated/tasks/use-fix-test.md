---
type: task
name: use-fix-test
tags: [skill, task]
source: plugin/skills/fix-test/SKILL.md
---

# Task: Use the fix-test skill

Auto-diagnose and fix failing tests — up to 3 attempts with re-runs. Triggers on: fix test, failing test, broken test, test error, why is this test failing, debug test.

Invoke with: `/fix-test <test file or pattern>`

## Steps

1. **Define target**
   "Which test is failing? A specific file, test name, or should I find failures automatically?"

2. **Define context**
   "Did this start failing after a recent change, or has it been broken?"

3. **Run the tool**
   ### Step 1: Identify Failures

   Run the failing test(s) to capture the error:

   ```bash
   uv run pytest <target> -v --tb=short 2>&1 | tail -40
   ```

4. **Run tool (option 2)**
   ### Step 2: Diagnose Root Cause

   Common failure patterns:

   | Pattern | Root Cause | Fix |
   | ------- | ---------- | --- |
   | `ModuleNotFoundError` | Import path changed | Update import |
   | `AttributeError: mock` | Mock target wrong | Match import path |
   | `AssertionError` | Expected value drift | Update assertion |
   | `TypeError: __init__` | Constructor changed | Update call site |
   | `FileNotFoundError` | Fixture path wrong | Use `tmp_path` |

   ### Step 3: Apply Fix and Re-run

   Apply the fix, then re-run the test. If it still fails,
   diagnose again with the new error. Repeat up to 3 times.

   ```bash
   uv run pytest <target> -v --tb=short
   ```

5. **Review output example**
   ### Step 4: Report

   After fixing (or exhausting 3 attempts), report:

   ```markdown
   ## Fix Test Results

   **Tests Fixed:** X/Y | **Attempts Used:** Z/3

   ### Fixed
   | Test | Root Cause | Fix Applied |
   |------|------------|-------------|

   ### Still Failing (if any)
   | Test | Error | Attempts | Notes |
   |------|-------|----------|-------|
   ```

6. **Choose follow-up action**
   Want me to generate missing tests for the fixed module?; Should I check for similar failures elsewhere?; Want a deeper look at the root cause?


## Related Topics
- **Reference**: Skill: fix-test — full reference
