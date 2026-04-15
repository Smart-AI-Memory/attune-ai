---
type: tip
feature: smart-test
depth: tip
generated_at: 2026-04-14T14:44:34.129692+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Tip: working effectively with smart test

## Context

Find untested code and generate pytest tests with edge cases.

## Recommendations

1. **Start with `ParallelTestGenerationWorkflow` for bulk test creation.** It discovers low-coverage modules and generates tests in batches using multi-tier LLMs. Running `discover_low_coverage_modules()` first shows you exactly which modules need attention without generating anything yet.

2. **Use `ASTFunctionAnalyzer` for precise function analysis before writing custom test generators.** It extracts function signatures, parameter types, and complexity metrics that determine what test cases you actually need. The `analyze()` method returns structured data about async functions, exceptions, and side effects that template generators miss.

3. **Parse existing coverage with `parse_coverage_json()` rather than guessing what needs testing.** Point it at your `coverage.json` file to get `ModuleCoverage` objects with exact line numbers and priority scores. This prevents wasting time on already-covered code.

## Why this matters

The smart-test workflows analyze your actual codebase structure and coverage gaps instead of generating generic tests. Starting with coverage analysis and AST parsing means you write fewer, more targeted tests that catch real issues.

## Source files

- `src/attune/workflows/test_gen/**`
- `src/attune/workflows/test_audit/**`
- `src/attune/workflows/test_gen_parallel.py`

**Tags:** `tests`, `coverage`, `generation`
