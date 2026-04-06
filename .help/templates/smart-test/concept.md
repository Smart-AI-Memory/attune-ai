---
feature: smart-test
depth: concept
generated_at: 2026-04-06T04:27:43.933443+00:00
source_hash: 0e86de76d767be8bdf8056850e5e91c4a526aa1b59d9a50dbb63b86e27ed9c03
status: generated
---

# Smart Test

## How it works

Find untested code and generate pytest tests with edge cases.

The main building blocks are:

- **`ASTFunctionAnalyzer`** — Analyzes function signatures and structure using Abstract Syntax Trees for precise test generation.
- **`FunctionSignature`** — Captures detailed function metadata including parameters, return types, and documentation for test planning.
- **`ClassSignature`** — Captures detailed class metadata including methods, attributes, and inheritance for comprehensive test coverage.
- **`TestGenerationWorkflow`** — Orchestrates test creation using three specialized AI subagents that analyze code, generate test cases, and validate output.
- **`ModuleCoverage`** — Tracks which lines and functions have existing test coverage to identify gaps.

Under the hood, this feature spans 24 source
files covering:

- Test Generation Workflow Package
- AST-based Function and Class Analyzer
- Test Generation Configuration

## What connects to it

This feature relates to: tests, coverage, generation.

Other parts of the codebase interact with
smart test through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ASTFunctionAnalyzer` | Analyzes function signatures and structure using Abstract Syntax Trees for precise test generation. | `src/attune/workflows/test_gen/ast_analyzer.py` |
| `FunctionSignature` | Captures detailed function metadata including parameters, return types, and documentation for test planning. | `src/attune/workflows/test_gen/data_models.py` |
| `ClassSignature` | Captures detailed class metadata including methods, attributes, and inheritance for comprehensive test coverage. | `src/attune/workflows/test_gen/data_models.py` |
| `TestGenerationWorkflow` | Orchestrates test creation using three specialized AI subagents that analyze code, generate test cases, and validate output. | `src/attune/workflows/test_gen/workflow.py` |
| `ModuleCoverage` | Tracks which lines and functions have existing test coverage to identify gaps. | `src/attune/workflows/test_audit/coverage_parser.py` |
