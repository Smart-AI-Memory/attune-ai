---
type: warning
feature: smart-test
depth: warning
generated_at: 2026-04-14T14:43:28.542698+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test cautions

## What to watch for

Smart-test generates pytest tests from AST analysis and runs parallel workflows with multiple LLM tiers. The automated nature of test generation creates specific risks around code correctness and resource consumption.

## Risk areas

**Generated test code may not compile or run**
The `generate_test_for_function()` and `generate_test_for_class()` functions produce executable Python code using template strings and type inference. When the AST analysis misidentifies parameter types or return types, the generated tests contain invalid assertions or import statements that cause pytest to fail.

**Coverage parsing fails silently on malformed JSON**
The `parse_coverage_json()` function raises `ValueError` for invalid JSON structure, but the calling workflows may not handle this gracefully. If pytest-cov generates unexpected output format, test generation workflows can proceed with empty module lists, appearing to succeed while doing nothing.

**Parallel workflows consume excessive LLM tokens**
`ParallelTestGenerationWorkflow` processes modules in configurable batches (default 10) and makes multiple API calls per module. With the default `top=200` modules, a single execution can generate thousands of LLM requests. Without proper rate limiting, this can exceed API quotas or incur unexpected costs.

**Type hint inference produces unsafe test values**
The `get_param_test_values()` function returns hardcoded test values like `"test_value"` for string parameters. For functions that expect specific formats (URLs, file paths, JSON), these generic values will cause the generated tests to fail or produce misleading results about actual code behavior.

**AST analysis misses runtime behavior**
`ASTFunctionAnalyzer` determines complexity and side effects through static analysis only. Functions that make network calls, modify global state, or have dynamic behavior based on runtime conditions will be analyzed incorrectly, leading to insufficient test coverage in critical areas.

## How to avoid problems

**Validate generated tests before committing**
Run `pytest` on the generated test files immediately after generation. The smart-test workflows create executable code, but compilation errors and import failures are common. Fix or discard any tests that don't run successfully.

**Set conservative batch sizes for parallel generation**
Start with `batch_size=5` or lower when using `ParallelTestGenerationWorkflow` to avoid overwhelming LLM APIs. Monitor token usage in your first few runs to establish appropriate limits for your codebase size.

**Review coverage JSON structure before parsing**
Verify that your pytest-cov configuration produces the expected JSON format by examining a sample file before running test audit workflows. The parser expects a specific `"files"` key structure that can vary between coverage tool versions.

**Inspect generated assertions for type-specific logic**
Check the test methods created by `generate_test_cases_for_params()` for parameters that require specific value formats. Replace generic test values with realistic data that exercises actual code paths in your functions.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
