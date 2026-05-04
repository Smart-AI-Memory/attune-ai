---
type: concept
feature: smart-test
depth: concept
generated_at: 2026-05-04T02:24:42.064118+00:00
source_hash: b86ac2f6972679ac24d0b4be339fa687398a6c09ee172583c670574d00d15c9f
status: generated
---

# Smart Test

Smart-test analyzes your codebase to identify untested code and automatically generates pytest tests to cover the gaps. It combines coverage analysis with AST-based function inspection to create targeted tests with edge cases, boundary values, and error path validation.

## Architecture components

Smart-test orchestrates three specialized workflows that work together:

**Coverage auditing** — The `TestAuditWorkflow` uses three subagents (coverage-auditor, gap-analyzer, test-planner) to parse pytest-cov JSON output, identify modules below your coverage threshold, and prioritize them by risk and complexity.

**Code analysis** — The `ASTFunctionAnalyzer` inspects Python source files to extract function signatures, parameter types, return types, decorators, and complexity metrics. This feeds into both coverage gap detection and test generation.

**Test generation** — The `TestGenerationWorkflow` creates complete pytest files with parametrized test cases, boundary value tests, and exception handling tests based on the AST analysis.

## Data flow

The system processes modules through these stages:

1. **Coverage parsing** — `ModuleCoverage` objects capture statement counts, missing line numbers, and coverage percentages from pytest-cov output
2. **Prioritization** — Modules are ranked by coverage gaps, with adjustments for complexity and criticality
3. **AST analysis** — `FunctionSignature` and `ClassSignature` objects store detailed metadata about each testable unit
4. **Batch processing** — Related modules are grouped by subsystem for coherent test generation
5. **Test writing** — Complete pytest files are generated with assertions, fixtures, and parametrized cases

## When coverage gaps matter

Smart-test focuses on three high-impact gap types:

- **Untested public functions** — APIs with zero test coverage that could break silently
- **Missing error paths** — Exception handlers and edge cases that fail unpredictably in production
- **Boundary conditions** — Empty inputs, None values, and limits that users encounter but tests miss

The `prioritize_modules` function filters out modules below 50% coverage by default, since these represent the highest risk for regressions.
