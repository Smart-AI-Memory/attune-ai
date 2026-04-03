---
type: concept
name: tool-planning
tags: [planning, architecture, design]
source: plugin/skills/planning/SKILL.md
---

# Planning

Planning helps you think through features, architecture,
and TDD strategy before writing code. Instead of jumping
straight to implementation, you get a structured plan
with tasks, acceptance criteria, dependencies, and risk
flags — when changes are cheapest to make.

## Planning modes

| Mode | What it produces | Time | Use case |
|------|-----------------|------|----------|
| **Feature spec** | Goals, scope, non-goals, task breakdown with effort estimates | ~2-3 min | Starting a new feature or epic |
| **TDD scaffold** | Test-first structure with red/green/refactor steps and test names | ~1-2 min | Complex logic that needs test coverage from the start |
| **Architecture review** | Component analysis, coupling assessment, dependency map | ~2-3 min | Evaluating design decisions before committing to them |

## When you'd use it

Before starting a new feature — define what "done" looks
like and break the work into deliverables. When designing
a TDD approach — get a test-first skeleton with the right
granularity. When evaluating architecture — surface
coupling, circular dependencies, and scaling concerns
before they become expensive to fix.

## What it produces

| Output | Description |
|--------|-------------|
| Task breakdown | Ordered steps with effort estimates and dependencies |
| Acceptance criteria | Clear, testable definition of done per task |
| Risk assessment | Blockers, unknowns, and mitigation strategies |
| Scope boundaries | Explicit non-goals to prevent scope creep |
| Dependency map | What depends on what, and what can run in parallel |

## What to expect

When you ask for planning, you'll be guided through a
couple of quick questions first — what you're planning
and what kind of plan you need. This keeps the output
focused on your actual goal instead of producing a
generic plan. If you provide both details upfront (e.g.
"plan a user authentication feature") the questions are
skipped and it runs immediately.

Runs on your Claude subscription — no API key or
additional cost.

## Want to learn more?

- Say **"tell me more"** for step-by-step instructions
- Say **"what is spec?"** for spec-driven development
  with approval loops
- Say **"what is refactor plan?"** for code-level
  refactoring analysis
