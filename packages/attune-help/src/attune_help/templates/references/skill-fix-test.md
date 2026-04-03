---
type: reference
subtype: procedural
name: skill-fix-test
category: skill
tags: [testing, skill, plugin, reference]
source: plugin/skills/fix-test/SKILL.md
---

# Fix Test Reference

Complete reference for the fix-test skill -- every root
cause it handles, how the retry cycle works, and how to
interpret results.

## Invocation

```
/fix-test <test file, test name, or pattern>
```

Or natural language:

```
fix the failing test in test_auth.py
why is test_login_expired failing?
debug the broken tests in tests/unit/
```

Providing the target inline skips the scoping questions
and jumps directly to diagnosis.

## Scoping questions

If no target is provided, the skill asks:

1. **Which test?** -- "Which test is failing? A specific
   file, test name, or should I find failures
   automatically?"
2. **When did it break?** -- "Did this start failing
   after a recent change, or has it been broken a
   while?"

The answers guide diagnosis priority. Recent breakage
favors import errors and mock mismatches; long-standing
failures favor environment and fixture issues.

## How it works

The skill runs on your Claude subscription -- no API key
or additional budget needed.

1. Run the failing test and capture the traceback
2. Classify the error into a root cause category
3. Apply a targeted fix
4. Re-run the test to confirm the repair
5. If still failing, diagnose the new error and retry
   (up to 3 total attempts)
6. Report results

## Root cause categories

### Import errors

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `ModuleNotFoundError` | Module renamed or moved | Updates import path |
| `ImportError: cannot import name` | Symbol renamed | Updates imported name |
| `ModuleNotFoundError` (package) | Package removed from deps | Adds `pytest.importorskip()` |

### Mock mismatches

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `AttributeError` on mock | `patch()` target stale | Updates patch string to match current import |
| `AssertionError: Expected call` | Mock not wired to new path | Patches at the import site, not the source |
| `TypeError: unexpected keyword` | Mocked function signature changed | Updates mock spec or call args |

### Assertion drift

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `AssertionError: X != Y` | Return value changed | Updates expected value |
| `AssertionError: not True` | Boolean logic changed | Updates condition or expected result |
| `AssertionError` on output text | User-facing string changed | Updates string assertion |

### Type errors

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `TypeError: __init__()` | Constructor signature changed | Updates call-site arguments |
| `TypeError: missing argument` | Required param added | Adds the new parameter |
| `TypeError: unexpected keyword` | Parameter renamed or removed | Updates keyword name |

### Fixture issues

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `fixture 'X' not found` | Fixture renamed or removed | Updates fixture reference |
| `conftest not collected` | conftest.py in wrong directory | Moves or creates conftest |
| `FileNotFoundError` in fixture | Hardcoded path to test data | Switches to `tmp_path` |

### Environment issues

| Error pattern | Cause | Fix applied |
|---------------|-------|-------------|
| `KeyError` on env var | Missing environment variable | Adds `monkeypatch.setenv()` |
| `PermissionError` | CI runner permissions differ | Uses `tmp_path` instead of system dir |
| Platform-specific path error | Windows/macOS/Linux difference | Adds platform-aware assertion |

## Retry behavior

| Attempt | What happens |
|---------|-------------|
| **1st** | Initial diagnosis and fix based on the original traceback |
| **2nd** | Re-reads the new traceback; handles cascading issues (e.g., fixing the import reveals a mock mismatch) |
| **3rd** | Final attempt; if this fails, the test is reported as needing manual attention with a detailed explanation |

Each attempt diagnoses fresh from the latest error. The
skill does not repeat the same fix twice.

## Output format

```markdown
## Fix Test Results

**Tests Fixed:** 3/4 | **Attempts Used:** 2/3

### Fixed

| Test | Root Cause | Fix Applied | Attempt |
|------|------------|-------------|---------|
| test_login | Import error | Updated `auth.Session` to `auth.AuthSession` | 1/3 |
| test_logout | Mock mismatch | Patched at import site | 1/3 |
| test_refresh | Assertion drift + mock | Updated expected token format, then fixed mock | 2/3 |

### Still Failing

| Test | Error | Attempts | What to try |
|------|-------|----------|-------------|
| test_complex_flow | Database fixture removed | 3/3 | Rewrite with repository pattern |
```

## Common invocations

| Goal | What to say |
|------|-------------|
| Fix one test | `/fix-test tests/unit/test_auth.py::test_login` |
| Fix a whole file | `/fix-test tests/unit/test_auth.py` |
| Fix all failures | `/fix-test` then answer "find failures automatically" |
| Fix after a rename | "fix the tests broken by the auth refactor" |
| Fix CI failures | "fix the tests that failed in CI" |

## After fixing

| Goal | What to say |
|------|-------------|
| Fix more tests | "fix the rest of the failing tests" |
| Generate new tests | "generate tests for the refactored module" |
| Find similar breakage | "check for other tests with stale imports" |
| Run full suite | "run all tests to make sure nothing else broke" |
| Review the fix | "show me what was changed" |

## Want to learn more?

- Say **"what is fix-test?"** to go back to the overview
- Say **"how do I fix a failing test?"** for the
  step-by-step guide
- Say **"generate tests"** to create new tests with
  smart-test
- Say **"review my code"** for a broader code quality
  check
