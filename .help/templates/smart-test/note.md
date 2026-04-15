---
type: note
feature: smart-test
depth: note
generated_at: 2026-04-14T14:44:46.669486+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Note: smart test

## Context

Smart Test identifies untested code paths and generates comprehensive pytest test suites with edge cases and error handling scenarios.

## Architecture overview

Smart Test operates through three distinct workflows that address different aspects of test coverage:

**Test Generation Workflow** (`TestGenerationWorkflow`) uses three specialized subagents (function-identifier, test-designer, test-writer) to analyze code structure via AST parsing and generate targeted test cases.

**Test Audit Workflow** (`TestAuditWorkflow`) coordinates coverage analysis through three subagents (coverage-auditor, gap-analyzer, test-planner) to identify gaps in existing test suites and prioritize testing efforts.

**Parallel Test Generation Workflow** (`ParallelTestGenerationWorkflow`) combines multi-tier LLM processing with batch operations to generate behavioral tests at scale, processing up to 200 modules in configurable batch sizes.

## Core components

The `ASTFunctionAnalyzer` extracts detailed function signatures including parameter types, return types, exception patterns, and complexity metrics. It produces `FunctionSignature` and `ClassSignature` dataclasses that capture all metadata needed for intelligent test generation.

Coverage analysis builds on pytest-cov output through `parse_coverage_json()` and `prioritize_modules()`, which convert raw coverage data into `ModuleCoverage` objects ranked by priority scores.

Test template generation uses type-aware parameter testing (`get_param_test_values()`) and return type assertions (`get_type_assertion()`) to create executable test cases that cover both happy paths and edge cases.

## Integration patterns

The system exposes both class-based and functional APIs. Functions like `generate_test_for_function()` and `generate_test_for_class()` provide direct access to test generation, while workflow classes orchestrate multi-step analysis and generation processes.

The `DEFAULT_SKIP_PATTERNS` constant defines which directories to ignore during code discovery, covering common build artifacts, virtual environments, and IDE files.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
