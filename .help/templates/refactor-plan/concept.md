---
type: concept
feature: refactor-plan
depth: concept
generated_at: 2026-05-04T02:27:48.047318+00:00
source_hash: 048ea0ef75e8eaeda7382792e46947bba2ddef4a450bb9395be4c8ba0c1d1f38
status: generated
---

# Refactor Plan

A refactor plan analyzes your codebase for technical debt and generates a prioritized roadmap to fix structural problems systematically.

## Core workflow

The `RefactorPlanWorkflow` coordinates three specialized subagents to produce a unified refactoring assessment:

- **debt-scanner** identifies code smells, complexity hotspots, and maintainability issues
- **impact-analyzer** evaluates the effort and risk of fixing each problem
- **plan-generator** synthesizes findings into an actionable roadmap with priority rankings

Each subagent focuses on its domain expertise, then the orchestrator combines their reports into a single document with overall tech debt scoring (0-100), prioritized refactoring opportunities, and concrete next steps.

## Report structure

The output follows a consistent format designed for both technical teams and stakeholders:

| Section | Content |
|---------|---------|
| **Summary** | Tech debt score and 2-3 sentence executive overview |
| **Refactoring** | Prioritized list with effort estimates (small/medium/large) and risk levels (low/medium/high) |
| **Suggestions** | Actionable next steps ordered by priority, including quick wins |

The workflow includes file paths and line numbers when citing specific issues, making it easy to locate and address problems in your IDE.

## Integration points

You can trigger refactor planning through the CLI entry point or integrate it programmatically using the `RefactorPlanWorkflow` class. The workflow accepts a codebase path and returns structured results that the report formatter converts into human-readable markdown.
