---
name: planning
description: "Development planning for new features, TDD approach, and architecture review. Use this for high-level strategy before implementation. For code-level refactoring analysis, use refactor-plan instead. Triggers on: plan, feature, architecture, design, TDD, strategy."
argument-hint: "<what to plan: feature, tdd, architecture>"
---

# Planning

High-level development planning and architecture design.
For code-level refactoring analysis (code smells,
duplication, complexity), use the `refactor-plan` skill.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `tdd` | Plan TDD approach |
| `architecture` | Architecture review |

## MCP Tools

| Tool | What It Does |
| ---- | ------------ |
| `research_synthesis` | Synthesize insights from multiple documents to inform planning |

Use `research_synthesis` when the user needs to gather
context from multiple files or docs before planning.

## Behavior

All planning uses `EnterPlanMode` to create a structured
plan for user approval before implementation.

Use `AskUserQuestion` to understand:

- **feature**: What feature? What problem? Scope?
- **tdd**: What behavior? What should tests verify?
- **architecture**: What system? Specific concerns?
