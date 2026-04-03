---
type: reference
subtype: procedural
name: skill-spec
category: skill
tags: [skill, plugin]
source: plugin/skills/spec/SKILL.md
---

# Spec Reference

Complete reference for spec-driven development -- every
phase, quality gate, output format, and resume behavior.
Runs on your Claude subscription -- no API key or
additional cost.

## Invocation

```
/spec <what to build, or 'resume'>
```

Or natural language:

```
build a caching layer for the API
brainstorm and build a notification system
plan and execute a refactor of the auth module
I want to build user authentication
resume my spec
```

## The guided flow

Spec uses a Socratic discovery pattern -- it asks
questions to understand your goal before proposing
anything. Here's what to expect at each entry point:

| Entry | What you're asked | Default if skipped |
|-------|-------------------|-------------------|
| New spec | "What would you like to build?" | N/A -- a goal is required |
| Resume | "Which in-progress spec?" | Most recent if only one |
| Import | "Path to the plan file?" | N/A -- a path is required |
| Execute | "Which saved spec to execute?" | Most recent if only one |

## All five phases

### Phase 1: Brainstorm

Explores the problem space before committing to an
approach. Spec asks about constraints, existing code
patterns, and success criteria.

| Step | Interaction | What spec asks |
|------|------------|----------------|
| Context | Understand the codebase state | "What exists today? Any patterns to follow?" |
| Problem | Clarify what needs to change | "What's the core problem? Who does it affect?" |
| Goals | Define success criteria | "What does done look like? What are must-haves?" |
| End state | Envision the result | "When this ships, what's different?" |

**Quality gate:** At least 2 viable approaches with
documented trade-offs before proceeding.

**Output:** Prose summary with approaches, trade-offs,
and a recommended path.

### Phase 2: Decompose

Breaks the chosen approach into ordered, implementable
tasks. Each task becomes an XML block with structured
metadata.

| Task field | What it contains | Example |
|------------|-----------------|---------|
| `id` | Unique identifier | `2.1` |
| `name` | Short descriptive name | `add-jwt-middleware` |
| `objective` | What this task accomplishes | "Create token validation middleware" |
| `files-to-create` | New files with structure specs | `src/auth/middleware.py` |
| `files-to-modify` | Existing files with change specs | `src/api/routes.py` |
| `validation` | Testable acceptance criteria | "Middleware rejects expired tokens" |
| `risks` | Known concerns with severity | "medium: Token rotation timing" |

**Quality gate:** Every task has at least one testable
acceptance criterion. No task modifies more than 5 files
(split larger tasks).

**Output:** Plan file saved to
`.claude/plans/{topic-slug}.md` containing prose
summary and XML task blocks.

### Phase 3: Review

Walks through each task highlighting gaps, risks, and
missing edge cases.

| Check | What spec looks for | Example finding |
|-------|--------------------|--------------------|
| Missing edge cases | Inputs or states not handled | "What happens if the token is empty?" |
| Dependency order | Tasks that should come first | "Task 4 uses the service from Task 2" |
| Risk assessment | Severity-tagged concerns | "Task 5 modifies auth -- higher blast radius" |
| Scope creep | Tasks that exceed the goal | "Task 7 adds logging -- defer to next spec?" |
| Test coverage | Tasks without test validation | "Task 3 has no validation criteria" |

**Quality gate:** No open questions or unaddressed
risks. User confirms the plan is complete.

**Output:** Annotated plan with risk flags and user
decisions.

### Phase 4: Approve

Final checkpoint before execution. Shows a summary:

```
Spec: user-auth-jwt
Tasks: 7  |  Files: 12  |  Estimated risk: low

  1. Add JWT dependency and config schema
  2. Create token generation service
  3. Add token validation middleware
  4. Wire auth middleware into routes
  5. Add refresh token rotation
  6. Write integration tests
  7. Update API documentation

Ready to start executing?
```

**Quality gate:** Explicit user approval. Choosing "go
back to review" returns to Phase 3.

**Output:** Locked plan. No further edits without
returning to review.

### Phase 5: Execute

Implements tasks one at a time. After each task:
quality gates run, results are shown, and you decide
what happens next.

| Step | What happens | What you see |
|------|-------------|-------------|
| Progress | Shows current position | `[====------] 4/10 tasks` |
| Implementation | Creates/modifies files per task spec | File diffs and new files |
| Quality gates | Automated checks on the result | Pass/fail with severity and score |
| Decision | You choose next action | Options based on severity |

**Severity-gated approval:**

| Severity | Score | Options |
|----------|-------|---------|
| **High** | < 50 | "Fix and retry" or "Acknowledge risk and continue" |
| **Medium** | 50-79 | "Approve and continue", "Redo with new instructions", or "Auto-run remaining" |
| **Low** | >= 80 | "Approve and continue", "Redo with new instructions", or "Auto-run remaining" |

"Auto-run remaining" executes all pending tasks with
automatic approval for passing gates. High-severity
results still pause for your decision.

**Output:** Working code, state file tracking progress,
quality gate results per task.

## Plan file format

Plans live in `.claude/plans/` as markdown files with
embedded XML:

```markdown
# User Auth with JWT

## Summary

Add JWT-based authentication to the API with token
rotation and middleware validation.

## Approach

Option A (chosen): Middleware-first with refresh tokens.

## Tasks

<task id="1" name="add-jwt-config">
  <objective>Add JWT dependency and config schema</objective>
  <files-to-create>
    <file path="src/auth/config.py">
      JWT settings dataclass with secret, expiry, issuer
    </file>
  </files-to-create>
  <validation>
    <check>Config loads from environment variables</check>
    <check>Missing required fields raise ValueError</check>
  </validation>
</task>

<task id="2" name="token-service">
  ...
</task>
```

## State tracking

Execution state is saved after every task decision:

| Field | What it tracks | Example |
|-------|---------------|---------|
| `plan_path` | Which plan is running | `.claude/plans/user-auth-jwt.md` |
| `completed` | Task IDs that passed | `["1", "2", "3"]` |
| `current` | Task currently executing | `"4"` |
| `status` | Overall state | `"in_progress"` |
| `decisions` | User choices per task | `{"3": "approved", "2": "redo"}` |

State file: `.claude/plans/{topic-slug}.state.json`

## Resuming a paused spec

When you invoke `/spec resume` or say "pick up where I
left off":

1. Spec scans `.claude/plans/` for state files with
   `status: "in_progress"`
2. If multiple exist, you choose which to resume
3. Execution continues from the next pending task
4. The progress bar shows what's already done

| Scenario | What happens |
|----------|-------------|
| One in-progress spec | Resumes immediately |
| Multiple in-progress specs | You pick which one |
| No in-progress specs | Offers to start new or import |
| Plan file was edited since last run | Re-reads tasks, preserves completed state |

Power users can edit the plan file between sessions.
Spec re-reads the XML on resume, so new tasks or
modified acceptance criteria take effect immediately.
Already-completed tasks are not re-run.

## Import

Load a plan from another project or a hand-written
spec file:

```
/spec import path/to/plan.md
```

The file must contain XML `<task>` blocks. If it does,
spec copies it to `.claude/plans/` and proceeds to
review. If it doesn't, spec offers to create a new
spec from the file's content as a starting brief.

## Critical rules

- **Always asks before executing** -- nothing runs
  without explicit approval at the approve gate
- **State saved after every decision** -- safe to
  interrupt at any point
- **Plan files are always editable** -- if you say
  "let me edit the plan," spec pauses and waits for
  you to re-invoke
- **Quality gates are mandatory** -- every task gets
  checked, no silent passes

## Want to learn more?

- Say **"what is spec?"** to go back to the overview
- Say **"how do I use spec?"** for the step-by-step
  walkthrough
- Say **"plan a feature"** for lighter planning
  without the execution phases
- Say **"review my code"** to run quality checks on
  existing code instead
