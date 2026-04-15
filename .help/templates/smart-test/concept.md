---
type: concept
feature: smart-test
depth: concept
generated_at: 2026-04-14T14:42:15.155857+00:00
source_hash: fba1c2a2d71f311df2cc2ff7847b4a7e0af065ff31f1020498301ed7bcfe4c56
status: generated
---

# Smart Test

Smart Test automatically identifies low-coverage Python modules and generates comprehensive pytest test suites using AI-powered code analysis.

## Architecture overview

Smart Test operates through a three-stage pipeline that analyzes your codebase, identifies testing gaps, and generates targeted test files:

1. **Code analysis** — `ASTFunctionAnalyzer` parses Python source files to extract function signatures, parameter types, return types, and complexity metrics
2. **Coverage assessment** — `ModuleCoverage` tracks statement coverage percentages and identifies specific missing lines from pytest-cov output
3. **Test generation** — Multi-tier workflows use specialized AI agents to create test templates and complete them with realistic test cases

The system processes modules in parallel batches, prioritizing those with the lowest coverage percentages first.

## Core components

**`ASTFunctionAnalyzer`** analyzes Python source code to extract detailed signatures for both functions and classes. It captures parameter types, return annotations, decorators, and docstrings to inform test generation.

**`FunctionSignature` and `ClassSignature`** store structured analysis results including complexity scores, side effect indicators, and exception specifications. These data models guide the AI agents in creating appropriate test scenarios.

**`TestGenerationWorkflow`** coordinates three specialized subagents: function-identifier extracts testable units, test-designer creates test case specifications, and test-writer produces executable pytest code.

**`ParallelTestGenerationWorkflow`** scales test generation across multiple modules simultaneously, using different LLM tiers for template creation versus completion to optimize cost and speed.

## Test generation strategies

The system generates test cases by analyzing parameter types and creating realistic test values. For example, `get_param_test_values()` returns `"test_value"` for string parameters and generates appropriate values for other types.

Coverage-driven prioritization ensures the most impactful modules are tested first. `prioritize_modules()` sorts by coverage percentage and filters out modules above the threshold, while `group_into_batches()` organizes work by subsystem.

Error handling and edge cases receive special attention through the analysis of function signatures that specify raised exceptions and complexity indicators.
