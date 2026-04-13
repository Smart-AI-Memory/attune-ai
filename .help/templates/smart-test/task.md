---
feature: smart-test
depth: task
generated_at: 2026-04-13T16:54:19.305672+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Work with smart test

Use smart test when you need to analyze code coverage gaps and automatically generate comprehensive pytest tests with edge cases for untested functions and classes.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/test_gen/**

## Steps

1. **Understand the current behavior.**
   Read the entry points to see what smart test
   does today before making changes.
   The primary functions are:
   - `format_test_gen_report()` in `src/attune/workflows/test_gen/report_formatter.py` — Format test generation output as a human-readable report.
   - `generate_test_for_function()` in `src/attune/workflows/test_gen/test_templates.py` — Generate executable tests for a function based on AST analysis.
   - `generate_test_cases_for_params()` in `src/attune/workflows/test_gen/test_templates.py` — Generate test cases based on parameter types.
   - `get_type_assertion()` in `src/attune/workflows/test_gen/test_templates.py` — Generate assertion for return type checking.
   - `get_param_test_values()` in `src/attune/workflows/test_gen/test_templates.py` — Get test values for a single parameter based on its type.
2. **Locate the right function to change.**
   Each function has a single responsibility. Read its
   docstring, parameters, and return type to confirm it
   owns the behavior you need to modify.

3. **Make your change.**
   Follow existing patterns in the file — naming
   conventions, error handling style, and logging.

4. **Run the related tests.**
   This catches regressions before they reach other
   developers. Target with `pytest -k "smart-test"`.

## Key files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

## Common modifications

Functions you are most likely to modify:

- `format_test_gen_report()` in `src/attune/workflows/test_gen/report_formatter.py`
- `generate_test_for_function()` in `src/attune/workflows/test_gen/test_templates.py`
- `generate_test_cases_for_params()` in `src/attune/workflows/test_gen/test_templates.py`
- `get_type_assertion()` in `src/attune/workflows/test_gen/test_templates.py`
- `get_param_test_values()` in `src/attune/workflows/test_gen/test_templates.py`
- `generate_test_for_class()` in `src/attune/workflows/test_gen/test_templates.py`
- `main()` in `src/attune/workflows/test_gen/workflow.py`
- `parse_coverage_json()` in `src/attune/workflows/test_audit/coverage_parser.py`
