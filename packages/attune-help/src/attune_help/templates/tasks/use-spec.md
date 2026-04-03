---
type: task
name: use-spec
tags: [skill, task]
source: plugin/skills/spec/SKILL.md
---

# How to Build From a Spec

## Quick start

Describe what you want to build:

```
/spec add user authentication with JWT tokens
```

Or use natural language:

```
I want to build a caching layer for the API
```

You'll be guided through brainstorm, decompose, review,
approve, and execute -- one phase at a time.

## Walking through each phase

### Phase 1: Brainstorm

Spec asks about your goal, constraints, and existing
code before proposing anything. Expect questions like:

- "What problem does this solve?"
- "Are there existing patterns in the codebase to follow?"
- "What are the must-haves vs nice-to-haves?"

Once the problem is clear, spec generates at least two
competing approaches with trade-offs.

| You see | What to do |
|---------|-----------|
| Two or more approaches with pros/cons | Pick one, or ask for a different angle |
| "Which approach fits best?" | Choose, or say "combine A and B" |

### Phase 2: Decompose

The chosen approach is broken into ordered tasks. Each
task has a name, description, files to touch, and an
acceptance criterion.

| You see | What to do |
|---------|-----------|
| Numbered task list with acceptance criteria | Review the breakdown -- add, remove, or reorder tasks |
| "Does this breakdown look right?" | Say yes, or explain what's missing |

The plan is saved to `.claude/plans/{topic-slug}.md`
as XML task blocks. Power users can edit this file
directly.

### Phase 3: Review

Spec walks through each task and highlights potential
gaps, risks, or missing edge cases.

| You see | What to do |
|---------|-----------|
| Risk flags on specific tasks | Decide whether to address now or accept the risk |
| "Any concerns before we lock the plan?" | Raise anything that feels off, or say it looks good |

### Phase 4: Approve -- the gate

Nothing executes until you approve. You'll see a final
summary:

```
Spec: user-auth-jwt
Tasks: 7  |  Files: 12  |  Estimated risk: low

Task 1: Add JWT dependency and config schema
Task 2: Create token generation service
Task 3: Add token validation middleware
Task 4: Wire auth middleware into routes
Task 5: Add refresh token rotation
Task 6: Write integration tests
Task 7: Update API documentation

Ready to start executing?
```

| You see | What to do |
|---------|-----------|
| "Ready to start executing?" | Say yes to begin, or "go back to review" |

### Phase 5: Execute

Tasks run one at a time. After each task completes,
quality gates run automatically and you're asked what
to do next:

| Quality result | Options you see |
|---------------|----------------|
| **High severity** (score < 50) | "Fix and retry" or "Acknowledge risk and continue" |
| **Medium/low severity** (score >= 50) | "Approve and continue", "Redo with new instructions", or "Auto-run remaining tasks" |

"Auto-run remaining" lets you step away -- all pending
tasks execute sequentially with automatic approval for
passing gates.

## Resuming a paused spec

Session ended mid-execution? Just say:

```
/spec resume
```

Or:

```
pick up where I left off
```

You'll see a list of in-progress specs with a progress
bar showing completed vs remaining tasks. Pick one and
execution continues from the next pending task.

## Choosing what to build

| Command | What happens |
|---------|-------------|
| `/spec add caching to the API` | New spec from a description |
| `/spec resume` | Resume an in-progress spec |
| `/spec import path/to/plan.md` | Load a plan from another project |
| "build a notification system" | Natural language triggers spec |
| "brainstorm and build a CLI tool" | Brainstorm-first spec flow |

## What to do after execution

| Goal | What to say |
|------|-------------|
| Run the tests it generated | "run the tests to verify" |
| Review the code it wrote | "review the changes" |
| Start a new spec | "build something else" |
| See what was completed | "show spec status" |
| Adjust and re-execute a task | "redo task 3 with..." |

## Want to learn more?

- Say **"tell me more about spec"** for the complete
  reference with all phases, gates, and output formats
- Say **"what is spec?"** to go back to the overview
- Say **"plan a feature"** for lighter planning without
  the full execution workflow
