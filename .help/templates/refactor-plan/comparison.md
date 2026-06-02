---
type: comparison
name: refactor-plan-comparison
feature: refactor-plan
depth: comparison
generated_at: 2026-06-02T10:56:02.712315+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Comparison: Refactor Plan vs alternatives

## Context

Refactor Plan scans your codebase for structural problems — god classes, duplicated blocks, high cyclomatic complexity, tight coupling — and produces a prioritized roadmap with effort estimates and risk levels. It coordinates three specialized subagents (`debt-scanner`, `impact-analyzer`, and `plan-generator`) to do this work, then synthesizes their findings into a single report.

This page helps you decide between running Refactor Plan, writing a custom static-analysis script, or using a general-purpose code review.

## Feature comparison

| Capability | Refactor Plan | Custom script | General code review |
|---|---|---|---|
| Prioritized roadmap (severity × effort × impact) | ✅ Built in | ❌ You build it | ⚠️ Ad hoc, not scored |
| Effort estimates per issue | ✅ small / medium / large | ❌ | ❌ |
| Risk levels per issue | ✅ low / medium / high | ❌ | ⚠️ Subjective |
| Three-subagent analysis (debt, impact, plan) | ✅ Orchestrated automatically | ❌ | ❌ |
| Human-readable report via `format_refactor_plan_report()` | ✅ | ❌ | ❌ |
| CLI entry point (`main()`) | ✅ | ✅ | ❌ |
| Covers code smells, duplication, complexity, coupling, naming, dead code | ✅ All categories | ⚠️ Whatever you code | ⚠️ Varies |
| Actionable fix suggestions with file + line citations | ✅ | ⚠️ Depends on tooling | ⚠️ Inconsistent |
| Setup required | None — invoke `/refactor-plan <path>` | High | Low |

## Tradeoffs

**Refactor Plan vs. a custom static-analysis script**

Refactor Plan produces a scored, ranked roadmap immediately — no toolchain to wire up. A custom script gives you full control over rules and output format, but you are responsible for scoring logic, prioritization, and report formatting. For one-off checks or CI rules that need machine-readable output in a specific schema, a custom script may be more appropriate. For everything else, Refactor Plan delivers a richer result with less effort.

**Refactor Plan vs. a general code review**

A general code review (`/review` or equivalent) gives you broad feedback on correctness, style, and logic. It does not produce a scored debt inventory or rank issues by effort-to-impact ratio. If you already know the code has structural problems and you need to justify refactoring time or decide what to fix first, Refactor Plan's structured roadmap is more actionable than review prose.

**Limitations of Refactor Plan**

- The `RefactorPlanWorkflow` surface (`execute(**kwargs)`) does not expose per-category filtering through the public API; focused analysis (e.g., duplication only) is available through the conversational interface (`/refactor-plan`), not programmatic calls.
- Because the workflow orchestrates subagents, it is heavier than a single-pass linter. Running it against a very large monorepo may be slower than a targeted script scoped to one package.
- `format_refactor_plan_report()` formats output for human reading. If you need structured data (JSON, SARIF) for downstream tooling, you will need to process `WorkflowResult` directly rather than using the report formatter.

## Use Refactor Plan when…

- You want a **prioritized roadmap** without building scoring logic yourself — Refactor Plan scores every issue by severity, effort, impact, and risk out of the box.
- You are about to **add features to a complex area** and need to know which structural problems to clear first.
- You need **data to justify refactoring work** to stakeholders — the scored report and effort estimates give you concrete numbers.
- You want to **act on results immediately** — the roadmap integrates with follow-on actions like targeted simplification or test generation.

**Use a custom script instead when** you need machine-readable output in a specific format, you are enforcing a small set of hard rules in CI, or the analysis scope is narrow enough that a single-pass linter covers it.

**Use a general code review instead when** your concern is correctness or style across the whole codebase, not structural debt specifically.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
