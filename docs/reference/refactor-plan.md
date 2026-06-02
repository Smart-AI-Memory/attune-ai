# Refactor Plan CLI Reference

Detect code smells and generate a prioritized refactoring roadmap.

## Description

`refactor-plan` runs the `RefactorPlanWorkflow`, which coordinates three specialized subagents (`debt-scanner`, `impact-analyzer`, and `plan-generator`) to analyze a codebase and produce a unified refactoring roadmap. It writes a human-readable report to stdout, scoring overall tech debt and listing prioritized refactoring opportunities with effort estimates and risk levels.

## Usage

```
refactor-plan [OPTIONS] PATH
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--help` | — | Show this help message and exit |

## Output

On success, the command prints a formatted report with three sections:

```
## Summary
Overall tech debt score (0-100) and a 2–3 sentence executive summary
of the refactoring opportunities found.

## Refactoring
Prioritized list of refactoring opportunities with effort estimates
(small/medium/large) and risk levels (low/medium/high) for each item.

## Suggestions
Actionable next steps ordered by priority, including quick wins and
longer-term improvements.
```

A realistic excerpt:

```
## Summary
Score: 64/100

Three high-priority issues were found in src/engine.py and src/utils.py.
Structural complexity and duplicated logic are the dominant sources of debt.

## Refactoring
1. [High Impact / Low Effort / Risk: Medium]
   src/engine.py:45 — God class with 14 responsibilities
   Fix: Split into Engine + Parser + Validator

2. [High Impact / Low Effort / Risk: Low]
   src/utils.py:89 — Logic duplicated in 4 places
   Fix: Extract to shared helper

## Suggestions
- Start with src/utils.py deduplication (~30 min, low risk)
- Refactor src/engine.py god class before adding new features
- Add tests for src/engine.py before making structural changes
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Workflow completed and report written successfully |
| `1` | Workflow failed — invalid path, subagent error, or unhandled exception |

## Related commands

- `/refactor-plan` — Claude Code skill that invokes this workflow interactively
- `code-review` — run a general code quality review instead of a refactoring roadmap
- `security-audit` — scan for vulnerabilities rather than structural debt

<!-- attune-generated: source_hash=048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38 feature=refactor-plan kind=cli-reference generated_at=2026-06-02 -->
