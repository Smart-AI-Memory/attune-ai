# Smart Test architecture

Find untested code and generate pytest tests with edge cases.

## Purpose

The smart-test subsystem locates under-tested Python code and generates pytest tests for it. It owns two distinct workflows: a **test audit** that parses coverage data, prioritizes modules by gap severity, and coordinates LLM subagents to produce a structured coverage report; and a **test generation** workflow that uses AST analysis to extract function and class signatures and then writes executable pytest tests, including edge cases, error paths, and parametrized combinations. The subsystem does not run pytest itself, manage test fixtures across projects, or decide which tests to delete — those concerns belong to the caller or to CI tooling.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `ModuleCoverage` | Holds parsed coverage metrics (statements, covered lines, missing lines, priority score) for one module. | `src/attune/workflows/test_audit/coverage_parser.py` |
| `TestAuditWorkflow` | Orchestrates three named subagents (`coverage-auditor`, `gap-analyzer`, `test-planner`) to audit the test suite and synthesize a structured markdown report. | `src/attune/workflows/test_audit/workflow.py` |
| `ASTFunctionAnalyzer` | Walks Python ASTs to extract `FunctionSignature` and `ClassSignature` records; handles sync, async, and nested class definitions. | `src/attune/workflows/test_gen/ast_analyzer.py` |
| `FunctionSignature` | Carries the full static profile of a function (params with types, return type, raises set, async flag, complexity, decorators) consumed by test generators. | `src/attune/workflows/test_gen/data_models.py` |
| `ClassSignature` | Carries the static profile of a class (methods, `__init__` params, base classes, enum/dataclass flags) consumed by test generators. | `src/attune/workflows/test_gen/data_models.py` |
| `TestGenerationWorkflow` | Orchestrates three named subagents (`function-identifier`, `test-designer`, `test-writer`) to analyze a codebase path and produce a test generation report. | `src/attune/workflows/test_gen/workflow.py` |
| `TestGenerationTask` | Tracks the lifecycle (`pending` → completed/failed) of one module's test generation job within the parallel workflow. | `src/attune/workflows/test_gen_parallel.py` |
| `ParallelTestGenerationWorkflow` | Discovers low-coverage modules, fans out test generation across batches using a two-stage AI pipeline (template then completion), and writes results to `tests/behavioral/generated/`. | `src/attune/workflows/test_gen_parallel.py` |

## Data flow

The system has two entry paths that share the AST analysis layer but diverge at output:

```
                          ┌─────────────────────────────────────────┐
                          │           Audit path                    │
                          │                                         │
  coverage.json ──► parse_coverage_json()                          │
                       │                                            │
                       ▼                                            │
               list[ModuleCoverage]                                 │
                       │                                            │
                       ▼                                            │
             prioritize_modules()                                   │
                       │                                            │
                       ▼                                            │
             group_into_batches()                                   │
                       │                                            │
                       ▼                                            │
           TestAuditWorkflow.execute()                              │
            ├─► coverage-auditor subagent                          │
            ├─► gap-analyzer subagent                              │
            └─► test-planner subagent                              │
                       │                                            │
                       ▼                                            │
             Structured audit report ◄───────────────────────────┘

                          ┌─────────────────────────────────────────┐
                          │         Generation path                 │
                          │                                         │
  source files ──► ASTFunctionAnalyzer.analyze()                   │
                       │                                            │
                       ▼                                            │
        list[FunctionSignature] + list[ClassSignature]             │
                       │                                            │
          ┌────────────┴────────────┐                              │
          ▼                         ▼                              │
  generate_test_for_function()  generate_test_for_class()         │
          └────────────┬────────────┘                              │
                       ▼                                            │
           TestGenerationWorkflow.execute()                        │
            ├─► function-identifier subagent                       │
            ├─► test-designer subagent                             │
            └─► test-writer subagent                               │
                       │                                            │
                       ▼                                            │
             format_test_gen_report()                              │
                       │                                            │
                       ▼                                            │
             Test generation report ◄────────────────────────────┘

  Parallel variant (ParallelTestGenerationWorkflow):

  source files ──► discover_low_coverage_modules()
                       │
                       ▼  (top N modules, batched)
              analyze_module_structure()
                       │
                       ▼
        generate_test_template_with_ai()   ← stage 1 LLM
                       │
                       ▼
          complete_test_with_ai()          ← stage 2 LLM
                       │
                       ▼
          process_module_batch() ──► list[TestGenerationTask]
                       │
                       ▼
          tests/behavioral/generated/
```

## Design decisions

**Two separate workflows instead of one.** Audit and generation have different LLM subagent sets and different output contracts. Merging them into one workflow would couple the prioritization logic (which needs `coverage.json`) to the AST analysis logic (which works purely from source). Keeping them separate lets you run an audit without generating tests, or generate tests for a handpicked module without running a full coverage audit first.

**AST analysis before LLM generation.** `ASTFunctionAnalyzer` extracts precise signatures — parameter types, raises declarations, async flags, complexity scores — before any LLM subagent is invoked. This means the test-designer and test-writer subagents receive structured, accurate metadata rather than having to infer signatures from raw source, which reduces hallucinated parameter names and incorrect assertion types.

**Parallel workflow as a separate class.** `ParallelTestGenerationWorkflow` uses a two-stage LLM pipeline (template generation, then completion) and operates on batches of up to 200 modules. Rather than adding batch-mode flags to `TestGenerationWorkflow`, this concern is encapsulated in its own class to avoid complicating the simpler single-module path. The tradeoff is a third workflow class to maintain.

**Prompt templates as module-level constants.** `AUDIT_SYSTEM_PROMPT`, `PLAN_SYSTEM_PROMPT`, and `BATCH_TASK_TEMPLATE` are string constants in the prompts module rather than hardcoded inside workflow methods. This makes prompt iteration possible without touching workflow logic, and the constants are importable for testing in isolation.

## Extension points

- **Add a new coverage source format:** implement a parser with the same signature as `parse_coverage_json(json_path: str) -> list[ModuleCoverage]` and pass the resulting list directly to `prioritize_modules()`. No changes to the workflow classes are needed.

- **Change module prioritization logic:** replace or wrap `prioritize_modules()` in `src/attune/workflows/test_audit/coverage_parser.py`. The function returns a sorted, filtered `list[ModuleCoverage]`; `TestAuditWorkflow` consumes whatever list it receives.

- **Add a new subagent to the audit:** extend `_SUBAGENT_NAMES` in `src/attune/workflows/test_audit/workflow.py` and update `_TASK_PROMPT_TEMPLATE` to include the new agent's section. The orchestrator prompt in `_SYSTEM_PROMPT` should be updated to name the new agent's domain.

- **Support a new language or AST structure:** subclass `ASTFunctionAnalyzer` and override `visit_FunctionDef`, `visit_AsyncFunctionDef`, and `visit_ClassDef`. The `analyze()` method returns `(list[FunctionSignature], list[ClassSignature])`; downstream generators consume those dataclasses directly.

- **Add a custom test template:** `BATCH_TASK_TEMPLATE` in the prompts module is a plain Python format string with named fields (`batch_id`, `subsystem`, `target_pct`, `missing_lines_summary`, `source_path`, `key_signatures`, `test_path`, `test_class_specs`, `module`). Substitute a different template string to change the structure of generated test files without touching `ParallelTestGenerationWorkflow`.

For usage questions — how to invoke `/smart-test` or interpret its output — see the concept doc (`concepts/tool-smart-test.md`) and quickstart (`quickstarts/skill-smart-test.md`).
