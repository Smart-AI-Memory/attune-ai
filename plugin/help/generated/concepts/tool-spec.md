---
name: tool-spec
source: plugin/skills/spec/SKILL.md
summary: This template guides developers through a structured five-phase workflow—brainstorm,
  decompose, review, approve, and execute—that establishes a detailed specification
  with quality gates before writing any code to prevent scope creep and ensure clarity
  on requirements, edge cases, and completion criteria.
tags:
- spec
- planning
- workflow
type: concept
---

# Spec-Driven Development

A structured workflow that moves from idea to working code through five phases: brainstorm, decompose, review, approve, and execute. Each phase has quality gates that prevent progress until the spec meets its acceptance criteria. The approval loop ensures you sign off before any code is generated.

## Why Use It

Starting to code without a spec invites scope creep and rework. Spec-driven development forces clarity upfront — what are we building, what are the edge cases, what does "done" look like — before a single line is written.

## When to Use It

- Any feature that touches three or more files
- Requirements that are ambiguous or still evolving
- Situations that require an auditable trail of design decisions
- Handoffs where another developer will own the implementation

## Workflow Phases

| Phase | What Happens | Gate |
|------------|----------------------------------------------|-------------------------------|
| Brainstorm | Explore the problem space; generate options | At least two approaches |
| Decompose | Break work into tasks with acceptance criteria | All tasks are testable |
| Review | Identify gaps, risks, and missing edge cases | No open questions remain |
| Approve | Sign off on the plan | Explicit user approval |
| Execute | Generate code following the spec | All previous gates passed |

## Related Topics

- **Task** — Use the spec skill: step-by-step walkthrough
- **Reference** — Skill: spec: full reference
