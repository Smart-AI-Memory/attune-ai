---
type: reference
subtype: procedural
name: skill-planning
category: skill
tags: [skill, plugin]
source: plugin/skills/planning/SKILL.md
---

# Planning Reference

Complete reference for the planning skill — every
planning mode, how plans are structured, and what
to do with the output. Runs on your Claude
subscription — no API key or additional cost.

## Invocation

```
/planning <what to plan>
```

Or natural language:

```
plan a user authentication feature
plan TDD for the payment module
review the architecture of the plugin system
help me plan the next sprint
design a caching strategy
```

## The guided flow

The skill uses a Socratic discovery pattern — it asks
questions to scope the work before running. Here's
what to expect:

| Step | What you're asked | Default if skipped |
|------|-------------------|-------------------|
| 1. Subject | "What are you planning?" | No default — must specify |
| 2. Mode | "Feature spec, TDD approach, or architecture review?" | Feature spec |

Provide both inline to skip the questions entirely:

```
plan TDD for src/auth/session.py
```

## All planning modes

### Feature spec

| Aspect | Detail |
|--------|--------|
| **Purpose** | Define a feature before building it |
| **Produces** | Goal, scope, non-goals, task breakdown, acceptance criteria, risks |
| **Time** | ~2-3 minutes |
| **Best for** | New features, epics, or multi-day work items |
| **Depth** | Tasks include effort estimates, dependencies, and explicit "done" criteria |

### TDD scaffold

| Aspect | Detail |
|--------|--------|
| **Purpose** | Plan a test-first implementation sequence |
| **Produces** | Red/green/refactor steps with test names and expected behavior |
| **Time** | ~1-2 minutes |
| **Best for** | Complex logic, algorithms, or code that needs high coverage |
| **Depth** | Each step names the test, states the assertion, and describes the minimal code to pass |

### Architecture review

| Aspect | Detail |
|--------|--------|
| **Purpose** | Evaluate design decisions before committing |
| **Produces** | Component analysis, coupling assessment, dependency map, scaling concerns |
| **Time** | ~2-3 minutes |
| **Best for** | New systems, major refactors, or pre-commit design validation |
| **Depth** | Identifies circular dependencies, high-coupling risks, and single points of failure |

## Output format

### Feature spec structure

```markdown
## Feature Plan: <Name>

### Goal
One-sentence description of what this feature does.

### Scope
- Included deliverable 1
- Included deliverable 2

### Non-goals
- Explicitly excluded item (deferred to Phase 2)

### Tasks
1. [Effort] Task name
   Acceptance: Testable criteria for "done"
   Depends on: Earlier task (if any)

### Risks
- Risk description
  Mitigation: How to handle it

### Estimated total: X hours
```

### TDD scaffold structure

```markdown
## TDD Plan: <Name>

### Red/Green/Refactor Steps

Step 1 — Red: test_<behavior>
  Write: <what the test asserts>
  Run: pytest -k <test_name> (should FAIL)

Step 2 — Green: implement <function>
  Write: <minimal code to pass>
  Run: pytest -k <test_name> (should PASS)

Step 3 — Refactor
  Extract: <what to clean up>
  Run: pytest (all should PASS)
```

### Architecture review structure

```markdown
## Architecture Review: <System>

### Components
| Component | Responsibility | Dependencies |
|-----------|---------------|--------------|
| auth      | User identity | db, cache    |
| api       | HTTP routing  | auth, models |

### Coupling Assessment
- auth ↔ db: Low (interface-based)
- api → auth: Medium (direct import)

### Dependency Map
api → auth → db
api → models → db

### Concerns
- Single point of failure: database
  Recommendation: Add connection pooling
- Circular risk: none detected

### Scaling Considerations
- auth: Stateless, scales horizontally
- db: Vertical scaling limit ~10k conn
```

## How plans are structured

Every plan follows the same principles regardless
of mode:

| Principle | What it means |
|-----------|--------------|
| **Scope boundaries** | Non-goals are explicit to prevent creep |
| **Testable criteria** | Each task has acceptance criteria you can verify |
| **Dependencies visible** | Tasks show what they depend on and what can run in parallel |
| **Risks surfaced early** | Blockers and unknowns listed with mitigation strategies |
| **Effort estimates** | Rough hour estimates per task for sprint planning |
| **Ordered by priority** | Most important or blocking tasks listed first |

## Follow-up actions

After a plan is generated, you'll be offered follow-up
options based on the mode:

| Goal | What to say | When it's offered |
|------|-------------|-------------------|
| Start building | "let's build task 1" | After feature spec |
| Refine a task | "add more detail to task 3" | After any plan |
| Switch modes | "now do TDD for the auth module" | Always |
| Turn into spec | "create a spec from this plan" | After feature spec |
| Review architecture | "review the architecture" | After feature spec |
| Export the plan | "export as markdown" | Always |
| Plan a different feature | "plan the billing module" | Always |

## Planning vs. related skills

| Skill | Focus | When to use instead |
|-------|-------|-------------------|
| **Planning** | High-level strategy before implementation | Starting something new |
| **Spec** | Spec-driven development with approval gates | Ready to execute with quality checks |
| **Refactor plan** | Code-level restructuring analysis | Improving existing code, not planning new features |
| **Brainstorm** | Open-ended idea exploration | Not sure what to build yet |

## Want to learn more?

- Say **"what is planning?"** to go back to the
  overview
- Say **"how do I plan?"** for the step-by-step
  guide
- Say **"create a spec"** to turn a plan into
  spec-driven development
- Say **"what is refactor plan?"** for code-level
  restructuring
