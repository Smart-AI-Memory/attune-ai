---
feature: smart-test
depth: reference
generated_at: 2026-04-13T16:54:28.731977+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ASTFunctionAnalyzer` | Analyzes Python functions using Abstract Syntax Tree parsing to extract metadata for test generation. | `src/attune/workflows/test_gen/ast_analyzer.py` |
| `FunctionSignature` | Stores function metadata including parameters, return types, and docstrings for test creation. | `src/attune/workflows/test_gen/data_models.py` |
| `ClassSignature` | Stores class metadata including methods, attributes, and inheritance for test creation. | `src/attune/workflows/test_gen/data_models.py` |
| `TestGenerationWorkflow` | Orchestrates test generation using three specialized AI agents for analysis, generation, and validation. | `src/attune/workflows/test_gen/workflow.py` |
| `ModuleCoverage` | Represents test coverage metrics and statistics for a Python module. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `TestAuditWorkflow` | Performs automated test coverage analysis using AI agents to identify gaps and recommend improvements. | `src/attune/workflows/test_audit/workflow.py` |
| `TestGenerationTask` | Manages the execution state and progress of individual test generation operations. | `src/attune/workflows/test_gen_parallel.py` |
| `ParallelTestGenerationWorkflow` | Generates behavioral tests concurrently across multiple modules using tiered language models. | `src/attune/workflows/test_gen_parallel.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `format_test_gen_report()` | Converts test generation results into formatted reports for human review. | `src/attune/workflows/test_gen/report_formatter.py` |
| `generate_test_for_function()` | Creates executable test methods for functions using AST-derived signatures and type information. | `src/attune/workflows/test_gen/test_templates.py` |
| `generate_test_cases_for_params()` | Produces test case variations based on function parameter types and constraints. | `src/attune/workflows/test_gen/test_templates.py` |
| `get_type_assertion()` | Generates type validation assertions for function return values in test code. | `src/attune/workflows/test_gen/test_templates.py` |
| `get_param_test_values()` | Produces appropriate test values for function parameters based on their declared types. | `src/attune/workflows/test_gen/test_templates.py` |
| `generate_test_for_class()` | Creates comprehensive test classes including setup, method testing, and teardown logic. | `src/attune/workflows/test_gen/test_templates.py` |
| `main()` | Provides command-line interface for executing test generation workflows. | `src/attune/workflows/test_gen/workflow.py` |
| `parse_coverage_json()` | Processes pytest-cov JSON output to extract module coverage statistics. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `prioritize_modules()` | Ranks modules by coverage priority and filters out those below specified thresholds. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `group_into_batches()` | Organizes modules into processing batches based on package structure and subsystem boundaries. | `src/attune/workflows/test_audit/coverage_parser.py` |

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

## Tags

`tests`, `coverage`, `generation`
