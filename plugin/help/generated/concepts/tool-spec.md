---
type: concept
name: tool-spec
tags: [spec, planning, workflow]
source: plugin/skills/spec/SKILL.md
---

# Spec-Driven Development

## What

A structured workflow that moves from idea to working code
through five phases: brainstorm, decompose, review, approve,
and execute. Each phase has quality gates that prevent
moving forward until the spec meets acceptance criteria.
The approval loop ensures you sign off before any code is
generated.

## Why

Starting to code without a spec leads to scope creep and
rework. Spec-driven dev forces clarity upfront -- what are
we building, what are the edge cases, what does done look
like -- before a single line is written.

## When to use

- For any feature that touches 3+ files
- When requirements are ambiguous or evolving
- To produce an auditable trail of design decisions
- When handing off implementation to another developer

## Workflow phases

| Phase | What happens | Gate |
|-------|-------------|------|
| Brainstorm | Explore problem space, generate options | At least 2 approaches |
| Decompose | Break into tasks with acceptance criteria | All tasks testable |
| Review | Check for gaps, risks, missing edge cases | No open questions |
| Approve | User signs off on the plan | Explicit approval |
| Execute | Generate code following the spec | All gates pass |

## Related Topics

- **Task**: Use the spec skill -- step-by-step
- **Reference**: Skill: spec -- full reference
