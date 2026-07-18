---
name: plan
description: Development planning and architecture
---
# plan

Development planning and architecture design.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `feature` | Plan a new feature |
| `refactor` | Plan refactoring |
| `architecture` | Architecture review |

## Usage

```bash
/plan                   # Ask what to plan
/plan feature           # Plan a feature
/plan refactor          # Plan refactoring
/plan architecture      # Architecture review
```

## Behavior

All planning tasks use `EnterPlanMode` to create
a structured plan for user approval before any
implementation.

**After every plan is approved**, follow the
[Post-Plan Handoff](#post-plan-handoff) process.

### feature

Use `AskUserQuestion` to understand:

- What feature? What problem does it solve?
- What's the scope? Which files/modules?
- Any constraints or preferences?

Then use `EnterPlanMode` to design the implementation
plan. After approval, follow Post-Plan Handoff.

### refactor

Use `AskUserQuestion` to understand:

- What code needs refactoring?
- What's the goal? (simplify, split, extract)
- Any constraints?

Then use `EnterPlanMode` to plan the refactoring.
After approval, follow Post-Plan Handoff.

### architecture

Use `AskUserQuestion` to understand:

- What system or subsystem to review?
- Any specific concerns?

Then analyze the codebase structure and provide
architectural recommendations. If the review
produces actionable changes, follow Post-Plan
Handoff.

## Post-Plan Handoff

**This section applies to ALL routes after a plan
is approved.**

### Step 1: Save the plan

Save the approved plan to `.claude/plans/` using
the [Plan File Format](#plan-file-format) below.

File naming convention:
`{route}-{slug}-{YYYY-MM-DD}.md`

Examples:

- `refactor-auth-module-2026-02-22.md`
- `feature-dark-mode-2026-02-22.md`

Ensure `.claude/plans/` directory exists before
writing.

### Step 2: Offer execution

Use `AskUserQuestion` to ask:

```yaml
question: "Plan saved to .claude/plans/{filename}.
  Ready to execute?"
header: "Next"
options:
  - label: "Execute now"
    description: "Start implementing — I'll carry
      the plan context forward so you won't need
      to re-explain anything"
  - label: "Save for later"
    description: "Plan is saved — pick it up later
      with /dev {route}"
```

### Step 3: Transition

- **Execute now**: Transition into the corresponding
  route with full plan context. Do NOT re-ask
  scoping questions — the plan already contains
  all needed context. Use this mapping:

| Plan Route | Execute Via |
| ---------- | ----------- |
| `/plan feature` | `/dev` (implement directly) |
| `/plan refactor` | `/dev refactor` |
| `/plan architecture` | (analysis only — no auto-execute) |

- **Save for later**: Confirm the file path and
  end gracefully. Tell the user they can resume
  with `/dev {route}` in a future session.

## Plan File Format

All saved plans MUST use this format:

```markdown
# {Title}

**Created:** {YYYY-MM-DD}
**Source:** /plan {route}
**Route:** {route}
**Status:** pending

## Problem

{1-2 sentence problem statement}

## Goals

- {Must-have 1}
- {Must-have 2}
- {Nice-to-have (marked as such)}

## End State

{Concrete description of what "done" looks like}

## Scope

- **Files:** {list of target files/directories}
- **Type:** {refactor | feature | architecture}

## Approach

1. {Step 1 with specific file references}
2. {Step 2}
3. {Step 3}

## Open Questions

- {Anything unresolved}
```

The **Route** and **Status** fields are required
for `/dev` plan detection. Update **Status** to
`in-progress` when execution begins and `completed`
when done.
