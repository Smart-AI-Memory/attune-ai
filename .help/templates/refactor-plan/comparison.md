---
type: comparison
feature: refactor-plan
depth: comparison
generated_at: 2026-04-14T14:53:37.621294+00:00
source_hash: 05ca199fb5b9d09ed7030f06c407e71de2e78a2433624c15a7beacf294de4d07
status: generated
---

# Comparison: Refactor Plan vs alternatives

## Context

The refactor-plan feature coordinates three specialized subagents (debt-scanner, impact-analyzer, and plan-generator) to detect code smells and generate a prioritized refactoring roadmap with effort estimates and risk assessments.

## Feature comparison

| Aspect | Refactor Plan | Manual code review | Static analysis tools |
|--------|---------------|-------------------|----------------------|
| **Coverage** | Multi-dimensional analysis via 3 subagents | Human expertise, limited scope | Syntax and pattern-based only |
| **Prioritization** | Built-in priority ranking with effort/risk scoring | Subjective, inconsistent | No prioritization |
| **Output format** | Structured markdown report with actionable next steps | Varies by reviewer | Raw findings lists |
| **Automation** | Fully automated workflow | Manual, time-intensive | Automated detection only |
| **Context awareness** | Understands codebase relationships | High contextual understanding | Limited to local patterns |

## When to use refactor plan

Use refactor plan when you need:

- **Comprehensive tech debt assessment** — The three-subagent approach provides broader coverage than single-purpose tools
- **Prioritized action items** — You get effort estimates (small/medium/large) and risk levels (low/medium/high) for each refactoring opportunity
- **Consistent methodology** — The structured workflow produces repeatable results across different codebases
- **Executive reporting** — The formatted output includes an overall tech debt score (0-100) and executive summary suitable for stakeholders

The CLI entry point (`main()`) makes it ideal for CI/CD integration or scheduled tech debt reviews.

## When NOT to use refactor plan

Avoid refactor plan when:

- **You need immediate, tactical fixes** — The comprehensive analysis takes time; for urgent hotfixes, manual inspection is faster
- **Your codebase is under 1000 lines** — The multi-subagent overhead isn't justified for small projects
- **You need domain-specific analysis** — The subagents focus on general code quality, not specialized concerns like security vulnerabilities or performance bottlenecks
- **You're doing exploratory refactoring** — For experimental changes or proof-of-concepts, the structured reporting adds unnecessary overhead

## Use refactor plan when...

Choose refactor plan if you need a systematic approach to tech debt with stakeholder-ready reporting. Choose manual review if you need deep domain expertise or are working on a specific, well-understood problem. Choose static analysis tools if you only need to catch specific patterns and don't require prioritization.

The refactor plan workflow is the clear winner for periodic tech debt assessments and cross-team refactoring initiatives where consistent methodology and clear communication matter more than speed.

## Source files

- `src/attune/workflows/refactor_plan.py`
- `src/attune/workflows/refactor_plan_report.py`

**Tags:** `refactor`, `tech-debt`, `complexity`
