---
type: concept
name: tool-attune-hub
tags: [hub, routing, discovery]
source: plugin/skills/attune-hub/SKILL.md
---

# Attune Hub

## What

The central natural language router for all Attune skills.
Accepts free-form descriptions of what you want to do and
routes to the correct skill -- security audit, code review,
test generation, planning, refactoring, or any other
registered workflow. Uses Socratic discovery to clarify
intent before dispatching.

## Why

With 13+ skills available, remembering which one to invoke
for each task adds cognitive overhead. The hub is the single
entry point -- describe your goal in plain English and it
figures out which skill to run, asking clarifying questions
when your intent is ambiguous.

## When to use

- As your default entry point for any Attune workflow
- When you are unsure which skill fits your task
- To discover skills you did not know existed
- When you want guided Socratic scoping before execution

## What it routes to

| Intent | Routed skill |
|--------|-------------|
| "find security issues" | security-audit |
| "review this code" | code-quality |
| "generate tests" | smart-test |
| "plan a feature" | planning |
| "prepare a release" | release-prep |
| "fix failing tests" | fix-test |
| "refactor this module" | refactor-plan |
| "write docs" | doc-gen |
| "predict bugs" | bug-predict |
| "run a workflow" | workflow-orchestration |

## Related Topics

- **Task**: Use the attune-hub skill -- step-by-step
- **Reference**: Skill: attune-hub -- full reference
