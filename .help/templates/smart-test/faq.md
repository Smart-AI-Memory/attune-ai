---
type: faq
feature: smart-test
depth: faq
generated_at: 2026-04-14T14:44:11.350773+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test FAQ

## What is smart test?

Smart test analyzes your codebase to find untested code and automatically generates pytest tests with edge cases.

## When should I use it?

Use smart test when you need to improve test coverage or generate tests for existing code. It's particularly helpful for:
- Identifying modules with low test coverage
- Creating comprehensive test suites for functions and classes
- Generating edge cases you might miss writing tests manually

## What's the main entry point?

The main workflows are:

- `TestGenerationWorkflow` — Generates tests using AI-powered analysis
- `TestAuditWorkflow` — Audits existing test coverage and identifies gaps
- `ParallelTestGenerationWorkflow` — Generates tests for multiple modules in parallel

For direct test generation, start with `generate_test_for_function()` or `generate_test_for_class()`.

## How do I analyze my code coverage?

Use `parse_coverage_json()` to load pytest-cov coverage data, then `prioritize_modules()` to identify which modules need tests most urgently. The coverage threshold defaults to 50%.

## Can I generate tests in batches?

Yes. `ParallelTestGenerationWorkflow` can process multiple modules at once. Use the `batch_size` parameter to control how many modules to process simultaneously, and `top` to limit the total number of modules.

## What types of test cases does it generate?

Smart test generates test cases based on function parameters and return types. It creates:
- Type-specific test values (strings, numbers, booleans, etc.)
- Edge cases for different parameter combinations
- Assertions for return type validation
- Tests for async functions and class methods

## How do I debug it?

Run the related tests first: `pytest -k "smart-test" -v`. If they pass but your code still fails, check that your coverage.json file exists and is valid. The `parse_coverage_json()` function will raise specific errors if the file is missing or malformed.

## Where are the source files?

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
