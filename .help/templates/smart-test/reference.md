---
feature: smart-test
depth: reference
generated_at: 2026-04-06T04:27:58.912480+00:00
source_hash: 0e86de76d767be8bdf8056850e5e91c4a526aa1b59d9a50dbb63b86e27ed9c03
status: generated
---

# Smart Test reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ASTFunctionAnalyzer` | Analyzes Python functions using Abstract Syntax Trees for accurate test generation. | `src/attune/workflows/test_gen/ast_analyzer.py` |
| `FunctionSignature` | Stores function metadata including parameters, return types, and docstrings for test creation. | `src/attune/workflows/test_gen/data_models.py` |
| `ClassSignature` | Stores class metadata including methods, attributes, and inheritance for test creation. | `src/attune/workflows/test_gen/data_models.py` |
| `TestGenerationWorkflow` | Orchestrates test creation using three specialized AI subagents for comprehensive coverage. | `src/attune/workflows/test_gen/workflow.py` |
| `ModuleCoverage` | Represents test coverage statistics and uncovered lines for a single Python module. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `TestAuditWorkflow` | Automatically audits test coverage and identifies gaps using AI agents. | `src/attune/workflows/test_audit/workflow.py` |
| `TestGenerationTask` | Manages the execution state and progress of individual test generation operations. | `src/attune/workflows/test_gen_parallel.py` |
| `ParallelTestGenerationWorkflow` | Generates behavioral tests concurrently using multiple language model tiers for efficiency. | `src/attune/workflows/test_gen_parallel.py` |

## Functions

| Function | Description | File |
|----------|-------------|------|
| `format_test_gen_report()` | Converts test generation results into structured, human-readable reports. | `src/attune/workflows/test_gen/report_formatter.py` |
| `generate_test_for_function()` | Creates executable unit tests for Python functions using AST analysis. | `src/attune/workflows/test_gen/test_templates.py` |
| `generate_test_cases_for_params()` | Creates test scenarios based on function parameter types and constraints. | `src/attune/workflows/test_gen/test_templates.py` |
| `get_type_assertion()` | Generates assertion statements for validating function return types. | `src/attune/workflows/test_gen/test_templates.py` |
| `get_param_test_values()` | Produces appropriate test values for function parameters based on their types. | `src/attune/workflows/test_gen/test_templates.py` |
| `generate_test_for_class()` | Creates comprehensive test classes with methods for testing class behavior. | `src/attune/workflows/test_gen/test_templates.py` |
| `main()` | Provides command-line interface for running test generation workflows. | `src/attune/workflows/test_gen/workflow.py` |
| `parse_coverage_json()` | Extracts coverage data from pytest-cov JSON output files. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `prioritize_modules()` | Ranks modules by coverage priority and filters out low-priority items. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `group_into_batches()` | Organizes modules into logical batches based on package structure. | `src/attune/workflows/test_audit/coverage_parser.py` |

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

## Tags

`tests`, `coverage`, `generation`
