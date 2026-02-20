---
name: plan
description: Development planning and architecture
category: primary
aliases: [p]
tags: [planning, architecture, tdd, feature, strategy]
version: "1.0.0"
question:
  header: "Planning"
  question: "What do you need to plan?"
  multiSelect: false
  options:
    - label: "Feature implementation"
      description: "Plan a new feature end-to-end"
    - label: "TDD plan"
      description: "Plan test-driven development approach"
    - label: "Refactoring plan"
      description: "Plan a refactoring effort"
    - label: "Architecture review"
      description: "Review or design system architecture"
---

# plan

Development planning and architecture design.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `tdd` | Plan TDD approach |
| `refactor` | Plan refactoring |
| `architecture` | Architecture review |

## Usage

```bash
/plan                   # Ask what to plan
/plan feature           # Plan a feature
/plan tdd               # Plan TDD approach
/plan refactor          # Plan refactoring
/plan architecture      # Architecture review
```

## Behavior

All planning tasks use `EnterPlanMode` to create
a structured plan for user approval before any
implementation.

### feature

Use `AskUserQuestion` to understand:

- What feature? What problem does it solve?
- What's the scope? Which files/modules?
- Any constraints or preferences?

Then use `EnterPlanMode` to design the implementation
plan.

### tdd

Use `AskUserQuestion` to understand:

- What behavior to implement?
- What should the tests verify?

Then plan the TDD cycle:

1. Write failing tests
2. Implement minimum code to pass
3. Refactor

### refactor

Use `AskUserQuestion` to understand:

- What code needs refactoring?
- What's the goal? (simplify, split, extract)
- Any constraints?

Then use `EnterPlanMode` to plan the refactoring.

### architecture

Use `AskUserQuestion` to understand:

- What system or subsystem to review?
- Any specific concerns?

Then analyze the codebase structure and provide
architectural recommendations.
