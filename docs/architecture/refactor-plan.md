# Refactor Plan architecture

Detect code smells and generate a prioritized refactoring roadmap.

## Purpose

The refactor-plan subsystem scans a codebase for structural problems — god classes, duplication, high cyclomatic complexity, tight coupling — and synthesizes findings into a prioritized roadmap with effort estimates and risk levels. It is explicitly not responsible for executing any refactoring changes, rendering output to a terminal or file (that belongs to `format_refactor_plan_report`), or managing the individual subagent implementations themselves.

## Key classes

| Class | Responsibility | File |
|-------|----------------|------|
| `RefactorPlanWorkflow` | Orchestrates three Agent SDK subagents (`debt-scanner`, `impact-analyzer`, `plan-generator`), collects their structured findings, and synthesizes them into a single `WorkflowResult`. | `workflows/refactor_plan.py` |

The report layer lives outside `RefactorPlanWorkflow` entirely — `format_refactor_plan_report` in `workflows/refactor_plan_report.py` converts the raw `dict` result into human-readable output, and `main()` in that same module provides the CLI entry point.

## Data flow

```
CLI (main())
    |
    v
RefactorPlanWorkflow.execute(path=...)
    |
    +---> debt-scanner subagent      (code smells, duplication, dead code)
    |
    +---> impact-analyzer subagent   (severity, effort, risk scoring)
    |
    +---> plan-generator subagent    (prioritized roadmap, quick wins)
    |
    v
WorkflowResult  (raw dict)
    |
    v
format_refactor_plan_report(result, input_data)
    |
    v
Human-readable report string
```

Each subagent focuses on its own domain and reports findings as structured markdown. `RefactorPlanWorkflow` receives all three outputs and synthesizes them into a unified report with Summary, Refactoring, and Suggestions sections, as defined in `_TASK_PROMPT_TEMPLATE`.

## Design decisions

**Three specialized subagents instead of one general agent.** Splitting analysis across `debt-scanner`, `impact-analyzer`, and `plan-generator` means each agent can be given a tightly scoped prompt and domain context. A single monolithic agent would need to trade depth for breadth across six detection categories simultaneously. The downside is that synthesis becomes the orchestrator's responsibility — `RefactorPlanWorkflow` must reconcile potentially conflicting findings from separate agents.

**Report formatting separated from workflow execution.** `format_refactor_plan_report` is a plain function in its own module rather than a method on `RefactorPlanWorkflow`. This means the workflow's `WorkflowResult` can be consumed programmatically without incurring any formatting logic, and the CLI (`main()`) composes the two independently. Adding a JSON or Markdown export variant requires only a new formatting function, not changes to the workflow.

## Extension points

- **Add or replace a subagent** by modifying the entries in `_SUBAGENT_NAMES` (`{'debt-scanner', 'impact-analyzer', 'plan-generator'}`). Each name corresponds to a subagent the orchestrator dispatches; adding a fourth (for example, a `security-scanner`) means extending that set and updating `_TASK_PROMPT_TEMPLATE` to instruct synthesis of its output.
- **Change orchestration behavior** by subclassing `RefactorPlanWorkflow` and overriding `execute()`. The base class accepts `**kwargs` throughout, so you can pass additional context (target language, ignore patterns) without altering the constructor signature.
- **Add a new report format** by writing a new function alongside `format_refactor_plan_report(result: dict, input_data: dict) -> str` in `workflows/refactor_plan_report.py`. Wire it into a new CLI entry point or call it directly — no changes to the workflow layer are needed.

For usage questions, see the task guide (`tasks/use-refactor-plan.md`) or the concept overview (`concepts/tool-refactor-plan.md`).

<!-- attune-generated: source_hash=048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38 feature=refactor-plan kind=architecture generated_at=2026-06-02 -->
