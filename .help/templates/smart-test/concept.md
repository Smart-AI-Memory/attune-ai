---
type: concept
name: smart-test-concept
feature: smart-test
depth: concept
generated_at: 2026-05-16T06:19:45.785002+00:00
source_hash: 2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc
status: generated
---

# Smart Test

Smart Test finds untested code in your Python codebase and generates pytest tests to cover it — including edge cases, error paths, and boundary values.

## How it works

Smart Test runs two coordinated workflows: a **test audit** that identifies coverage gaps, and a **test generation** pipeline that writes tests to close them.

### Coverage audit

`TestAuditWorkflow` orchestrates three specialized subagents — `coverage-auditor`, `gap-analyzer`, and `test-planner` — to produce a structured report. The audit reads pytest-cov's `coverage.json` output via `parse_coverage_json`, then uses `prioritize_modules` to rank modules by coverage gap. Modules below a 50% coverage threshold are surfaced first. The result is a report with four sections: an overall health score (0–100), raw coverage metrics, a list of untested code paths, and a prioritized plan with effort estimates.

`ModuleCoverage` is the data unit that flows through this stage — it tracks the source path, total statements, covered statements, missing line numbers, coverage percentage, and a computed priority score for each module.

### Test generation

Once gaps are identified, three subagents take over: `function-identifier`, `test-designer`, and `test-writer`. `ASTFunctionAnalyzer` inspects your source using Python's AST to extract `FunctionSignature` and `ClassSignature` records — capturing parameter types, return types, raised exceptions, async status, decorators, and cyclomatic complexity — without executing the code.

From those signatures, `generate_test_for_function` and `generate_test_for_class` produce executable pytest functions. `generate_test_cases_for_params` derives test values from type hints (for example, a `str` parameter gets `"test_value"`), and `get_type_assertion` adds a matching return-type assertion. For input combinations, the output uses `@pytest.mark.parametrize`.

For large codebases, `ParallelTestGenerationWorkflow` scales this up: it discovers the top-N lowest-coverage modules, generates a test template with one LLM call, then completes the test body with a second — processing up to 200 modules in configurable batches of 10, writing output to `tests/behavioral/generated/`.

### Batching and grouping

`group_into_batches` clusters modules by subsystem (package path) before handing them to the planner. Each batch becomes a structured XML task prompt — specifying the coverage target, missing line numbers, key signatures, and the test file path to create — so the writing subagent has everything it needs without re-reading the full codebase.

## When it matters

Use Smart Test when you need to answer "what isn't tested?" rather than guessing. Typical situations:

- You've added a new module or public API and want to catch gaps before they become regressions.
- Coverage has dropped below 80% and you need to find exactly what's missing, not just the percentage.
- You're bootstrapping a legacy codebase that has little or no test coverage.
- You want to verify that exception handlers and error paths actually execute, not just the happy path.

## Relationship to Fix Test

Smart Test and Fix Test are complementary. Smart Test generates tests for code that has no coverage. Fix Test diagnoses and repairs tests that already exist but are failing — for example after a refactor changes a function signature or moves a module. If your starting point is a broken CI pipeline, reach for Fix Test. If your starting point is untested code, reach for Smart Test.
