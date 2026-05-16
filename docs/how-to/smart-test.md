---
type: how-to
name: skill-smart-test
tags: [testing, coverage, generation]
source: plugin/skills/smart-test/SKILL.md
---

# How to use smart-test

Use this guide when you need to find untested code in a Python project and generate pytest tests to cover it — including edge cases, error paths, and boundary values.

## Quick start

Run `/smart-test` with the path you want to cover:

```
/smart-test src/auth/
```

Smart-test audits that path, ranks modules by coverage gap, and writes pytest functions targeting the highest-risk untested code. Results appear directly in your Claude Code conversation.

## How it works

Smart-test coordinates three specialized subagents in sequence:

1. **Coverage auditor** — parses `coverage.json` produced by `pytest-cov`, ranks modules by a priority score (statements × coverage gap), and filters out anything already above your threshold (default: 50%).
2. **Gap analyzer** — uses AST analysis to identify untested public functions, missing branches, unexercised exception handlers, and boundary values in the prioritized modules.
3. **Test writer** — generates working pytest functions with assertions, `@pytest.mark.parametrize` decorators for input combinations, and `pytest.raises` blocks for expected exceptions.

If you provide a specific path upfront, the scoping questions are skipped and the workflow runs immediately.

## Core API

These are the building blocks the workflow uses internally. You can call them directly if you want to script your own pipeline.

| Function or class | Purpose |
|---|---|
| `parse_coverage_json(json_path)` | Parse `pytest-cov`'s `coverage.json` into a list of `ModuleCoverage` objects |
| `prioritize_modules(modules, min_threshold)` | Sort by priority score and drop modules above the coverage threshold |
| `group_into_batches(modules, max_batches)` | Group prioritized modules into batches by subsystem (package path) |
| `generate_test_for_function(module, func)` | Generate executable pytest tests for a single function using AST-derived metadata |
| `generate_test_for_class(module, cls)` | Generate an executable pytest test class from AST-derived class metadata |
| `generate_test_cases_for_params(params)` | Produce test case values for a function's parameter list based on type hints |
| `get_param_test_values(type_hint)` | Return concrete test values for a single parameter type |
| `get_type_assertion(return_type)` | Return an assertion statement appropriate for a given return type |
| `format_test_gen_report(result, input_data)` | Format the generation result as a human-readable markdown report |
| `ASTFunctionAnalyzer` | Walk a module's AST to extract `FunctionSignature` and `ClassSignature` objects |
| `TestAuditWorkflow` | Orchestrate the full audit pipeline using Agent SDK subagents |
| `TestGenerationWorkflow` | Orchestrate test generation across prioritized modules using three subagents |
| `ParallelTestGenerationWorkflow` | Generate tests in parallel across up to 200 low-coverage modules in configurable batch sizes |
| `main()` | CLI entry point — runs `TestGenerationWorkflow` from the command line |

## Integration patterns

### Audit first, then generate

Run the audit workflow to get a ranked gap report, then feed the highest-priority modules directly into generation:

```python
from smart_test.audit import TestAuditWorkflow
from smart_test.generation import TestGenerationWorkflow

# Audit the codebase and surface the worst coverage gaps
audit = TestAuditWorkflow()
audit_result = audit.execute(src_path="src/")

# Generate tests for the top offenders
gen = TestGenerationWorkflow()
gen_result = gen.execute(path="src/payments/")
```

### Parse coverage data and batch by subsystem

If you already have a `coverage.json` file from a `pytest --cov` run, you can drive the workflow directly from it:

```python
from smart_test.coverage_parser import parse_coverage_json, prioritize_modules, group_into_batches

modules = parse_coverage_json("coverage.json")           # list[ModuleCoverage]
prioritized = prioritize_modules(modules, min_threshold=50.0)
batches = group_into_batches(prioritized, max_batches=5)

for batch in batches:
    print(batch["subsystem"], [m["path"] for m in batch["modules"]])
```

### Scale up with parallel generation

For large codebases, `ParallelTestGenerationWorkflow` processes up to 200 low-coverage modules in parallel batches and writes results to `tests/behavioral/generated/` by default:

```python
from smart_test.parallel import ParallelTestGenerationWorkflow

workflow = ParallelTestGenerationWorkflow()
result = workflow.execute(top=50, batch_size=10, output_dir="tests/behavioral/generated")
print(result)
```

## See also

- [Concept: Smart Test](../concepts/tool-smart-test.md) — what gap types smart-test catches and how it scores risk
- [Quickstart: /smart-test](../quickstarts/skill-smart-test.md) — one-liner invocation reference
- [Concept: Fix Test](../concepts/tool-fix-test.md) — auto-repair failing tests after a refactor

<!-- attune-generated: source_hash=2ed25e274258323117a16cf96fcb5bf0a40e45a9bb8c246d4abfdc74365cfabc feature=smart-test kind=how-to generated_at=2026-05-16 -->

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 59 (code fence) | error | `from smart_test.audit import …` — module not importable |
| Line 59 (code fence) | error | `from smart_test.generation import …` — module not importable |
| Line 76 (code fence) | error | `from smart_test.coverage_parser import …` — module not importable |
| Line 91 (code fence) | error | `from smart_test.parallel import …` — module not importable |
| Line 101 | error | `[Concept: Smart Test](../concepts/tool-smart-test.md)` — target does not exist |
| Line 102 | error | `[Quickstart: /smart-test](../quickstarts/skill-smart-test.md)` — target does not exist |
| Line 103 | error | `[Concept: Fix Test](../concepts/tool-fix-test.md)` — target does not exist |
