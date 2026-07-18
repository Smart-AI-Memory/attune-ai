---
name: dev
description: Developer tools (commits, reviews, refactoring)
---
# dev

Developer tools for daily coding workflows.

## Routes

| Subcommand | Action |
| ---------- | ------ |
| `review` | Code review workflow |
| `debug` | Debugging session |
| `refactor` | Refactoring session |
| `commit` | Stage and commit changes |
| `pr` | Create a pull request |
| `quality` | Code quality check |
| `perf-audit` | Performance audit |

## Usage

```bash
/dev                    # Ask what to do
/dev review             # Code review
/dev commit             # Stage and commit
/dev debug              # Debug session
/dev refactor           # Refactoring
/dev pr                 # Create PR
```

## Fast-Path Detection

When explicit args satisfy scoping, skip questions:

- `/dev commit --auto` → stage all + commit
- `/dev review ./src/auth` → review that path
- `/dev commit` → ask what to stage
- `/dev` → ask what to do

**Rule:** If input contains BOTH an action AND a
target (or `--auto` flag), proceed to execution.
If either is missing, use `AskUserQuestion`.

## Behavior

### Plan Detection (all routes)

Before starting scoping questions for any route,
check for saved plans from `/plan`:

1. Use `Glob` to check `.claude/plans/{route}-*.md`
   for the current route (e.g., `refactor-*.md`
   for `/dev refactor`)
2. If matching plans exist, use `Read` to check
   their **Status** field (skip `completed` plans)
3. If no pending plans match, proceed normally
   with the scoping flow below
4. If multiple pending plans match, show a list
   and let the user choose which one
5. If a pending/in-progress plan is found, use
   `AskUserQuestion` with these options:

- **"Yes, use this plan"**: Read the plan file.
  Update its **Status** to `in-progress`. Use
  the plan's **Scope** and **Approach** sections
  to drive execution. Do NOT re-ask scoping
  questions.
- **"No, start fresh"**: Proceed with the normal
  `AskUserQuestion` scoping flow below.

Example prompt:

```yaml
question: "I found a saved plan:
  {plan-title} ({date}). Pick up where you
  left off?"
header: "Plan"
options:
  - label: "Yes, use this plan"
    description: "Skip scoping — execute based
      on the saved plan"
  - label: "No, start fresh"
    description: "Ignore the plan and scope
      from scratch"
```

### review

Use `AskUserQuestion` to scope:

- Which files or path to review?
- Focus area: quality, security, performance, or all?

Then run:

```bash
uv run attune workflow run code-review --path <target>
```

### debug

Use `AskUserQuestion` to understand:

- What error or unexpected behavior?
- Which file or area?

Then investigate using Read, Grep, and Bash tools.

### refactor

Use `AskUserQuestion` to scope:

- Which file or module?
- What kind of refactoring? (extract, simplify, rename)

Then use EnterPlanMode to plan the refactoring.

### commit

Use `AskUserQuestion` to confirm:

- Which files to stage?
- What kind of change? (feature, fix, refactor)

Then use git to stage and commit with a conventional
commit message.

### pr

Use `AskUserQuestion` to confirm:

- Target branch?
- PR description scope?

Then use `gh pr create` to create the PR.

### perf-audit

Use `AskUserQuestion` to scope:

- Which path to audit?

Then run:

```bash
uv run attune workflow run perf-audit --path <target>
```

### quality

Use `AskUserQuestion` to scope:

- Which path to analyze?

Then run:

```bash
uv run attune workflow run bug-predict --path <target>
```
