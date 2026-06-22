---
type: quickstart
name: smart-test-quickstart
feature: smart-test
depth: quickstart
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: b1325f36412cbd67b36481e0f150de834b91392f8fa17c843f8aecd357d18b07
status: generated
---

# Quickstart: Smart Test

Find untested code and generate pytest tests with edge cases.

```
/smart-test <path or module to test>
```

**Result:** A coverage gap report ranked by risk, plus working pytest functions with assertions for untested functions, branches, and error paths.

## Prerequisites

- The project is cloned and installed locally
- `pytest-cov` has produced a `coverage.json` file for your project

## Steps

1. **Parse your coverage report.** Point `parse_coverage_json()` at the JSON file that `pytest-cov` wrote:

   ```python
   from attune.workflows.test_audit.coverage_parser import parse_coverage_json, prioritize_modules

   modules = parse_coverage_json("coverage.json")
   ```

   You'll get a list of `ModuleCoverage` objects, each with `path`, `stmts`, `covered`, `missing_lines`, and a `pct` score.

2. **Identify the highest-priority gaps.** Filter out modules above your coverage threshold (default 50%) and sort by priority:

   ```python
   targets = prioritize_modules(modules)
   print(targets[0].path, targets[0].pct)
   # src/attune/help/engine.py  23.4
   ```

   The module with the lowest coverage and the most uncovered statements appears first.

3. **Generate tests for the top module.** Run the test generation workflow against that path:

   ```
   attune workflow run test-gen --path src/attune/help/engine.py
   ```

   **Expected output:**

   ```
   ## Summary
   Analyzed 12 functions. Designed 31 test cases. Wrote 1 test file.

   ## Test Gaps
   - engine.py: _resolve_template — no branch coverage on missing-key path
   - engine.py: render — exception handler never triggered

   ## Suggestions
   1. Add parametrized tests for empty-input edge cases (low effort)
   2. Add error-path test for FileNotFoundError in parse_coverage_json (low effort)
   ```

   The generated file is written to `tests/behavioral/generated/`.

4. **Verify the tests pass.**

   ```
   pytest tests/behavioral/generated/ -v
   ```

   All generated tests should pass on the first run against your current codebase.

**Next:** Run `pytest --cov` again and re-run `prioritize_modules()` to confirm coverage improved for the module you targeted.
