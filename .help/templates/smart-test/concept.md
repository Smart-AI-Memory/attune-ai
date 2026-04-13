---
feature: smart-test
depth: concept
generated_at: 2026-04-13T16:54:11.732502+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test

## How it works

Analyzes Python code structure and generates comprehensive pytest test suites with behavioral edge cases based on AST analysis and coverage data.

The main building blocks are:

- **`ASTFunctionAnalyzer`** — Analyzes function signatures and parameters from abstract syntax trees to generate accurate test cases.
- **`FunctionSignature`** — Captures detailed function metadata including parameters, return types, and docstrings for test generation.
- **`ClassSignature`** — Extracts class structure information including methods and attributes for comprehensive test coverage.
- **`TestGenerationWorkflow`** — Orchestrates automated test creation using three specialized AI agents for analysis, generation, and validation.
- **`ModuleCoverage`** — Tracks which lines and branches are covered by existing tests to identify gaps.

Under the hood, this feature spans 12 source
files covering:

- AST-based Function and Class Analyzer.
- Test Generation Configuration.
- Test Generation Data Models.

## What connects to it

This feature relates to: tests, coverage, generation.

Other parts of the codebase interact with
smart test through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ASTFunctionAnalyzer` | Analyzes function signatures and parameters from abstract syntax trees to generate accurate test cases. | `src/attune/workflows/test_gen/ast_analyzer.py` |
| `FunctionSignature` | Captures detailed function metadata including parameters, return types, and docstrings for test generation. | `src/attune/workflows/test_gen/data_models.py` |
| `ClassSignature` | Extracts class structure information including methods and attributes for comprehensive test coverage. | `src/attune/workflows/test_gen/data_models.py` |
| `TestGenerationWorkflow` | Orchestrates automated test creation using three specialized AI agents for analysis, generation, and validation. | `src/attune/workflows/test_gen/workflow.py` |
| `ModuleCoverage` | Tracks which lines and branches are covered by existing tests to identify gaps. | `src/attune/workflows/test_audit/coverage_parser.py` |
