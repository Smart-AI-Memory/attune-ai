---
type: task
name: smart-test-task
feature: smart-test
depth: task
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: b1325f36412cbd67b36481e0f150de834b91392f8fa17c843f8aecd357d18b07
status: generated
---

# Work with smart test

Use smart test when you need to audit test coverage, extend gap-detection logic, or change how pytest tests are generated for uncovered functions and classes.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/workflows/test_gen/` and `src/attune/workflows/test_audit/`

## Steps

1. **Identify the function that owns the behavior you want to change.**

   The smart-test feature is split across two workflow packages. Locate your entry point in the table below:

   | Function | File | Responsibility |
   |---|---|---|
   | `parse_coverage_json()` | `test_audit/coverage_parser.py` | Parse pytest-cov's `coverage.json` output into `ModuleCoverage` objects |
   | `prioritize_modules()` | `test_audit/coverage_parser.py` | Sort modules by priority score and drop those below the coverage threshold |
   | `group_into_batches()` | `test_audit/coverage_parser.py` | Group modules into batches by subsystem (package path) |
   | `format_test_gen_report()` | `test_gen/report_formatter.py` | Format test generation output as a human-readable report |
   | `generate_test_for_function()` | `test_gen/test_templates.py` | Generate executable pytest tests for a function using AST analysis |
   | `generate_test_for_class()` | `test_gen/test_templates.py` | Generate an executable test class using AST analysis |
   | `generate_test_cases_for_params()` | `test_gen/test_templates.py` | Generate test cases based on parameter types |
   | `get_type_assertion()` | `test_gen/test_templates.py` | Generate a return-type assertion for a function |
   | `get_param_test_values()` | `test_gen/test_templates.py` | Return test values for a parameter based on its type hint |

   Read the function's docstring, parameters, and return type to confirm it owns the behavior you need.

2. **Check which workflow class calls your target function.**

   - `TestAuditWorkflow` — coordinates the coverage audit using three subagents (`coverage-auditor`, `gap-analyzer`, `test-planner`) and produces a structured report.
   - `TestGenerationWorkflow` — coordinates test generation using three subagents (`function-identifier`, `test-designer`, `test-writer`).
   - `ParallelTestGenerationWorkflow` — discovers low-coverage modules and generates behavioral tests in parallel batches.

   If your change affects orchestration rather than a single function, edit the relevant `execute()` method directly.

3. **Make your change.**

   Key details to keep consistent:
   - `parse_coverage_json()` raises `FileNotFoundError` when the coverage file is missing and `ValueError` when the JSON structure is invalid or the `files` key is absent. Preserve these error types and messages if you touch the parser.
   - `prioritize_modules()` filters out modules below `min_threshold` (default `50.0`). If you change the threshold logic, update the default parameter value rather than hardcoding a number inside the function body.
   - `get_param_test_values()` returns `"test_value"` as the string literal for unrecognized types. Keep this fallback in place so test generation never produces empty parameter lists.
   - `DEFAULT_SKIP_PATTERNS` controls which directories `ParallelTestGenerationWorkflow` ignores during module discovery. Add new patterns to this constant rather than filtering inline.

4. **Run the related tests.**

   ```
   pytest -k "smart_test or test_audit or test_gen" -v
   ```

   Fix any failures before moving on.

5. **Verify end-to-end output.**

   Run the full audit workflow against a known directory and confirm the report contains the expected sections:

   ```
   /smart-test src/<your-module>/
   ```

   The output should include a **Summary** with a test health score, a **Coverage** section with line and function metrics, a **Test Gaps** section listing untested functions by priority, and a **Suggestions** section with a prioritized test plan.

## Key files

- `src/attune/workflows/test_audit/coverage_parser.py`
- `src/attune/workflows/test_gen/report_formatter.py`
- `src/attune/workflows/test_gen/test_templates.py`
- `src/attune/workflows/test_gen_parallel.py`
