---
name: dev
description: Developer tools (commits, reviews, refactoring)
category: primary
aliases: [d]
tags: [development, commit, review, refactor, debug]
version: "1.0.0"
question:
  header: "Dev action"
  question: "What do you need to do?"
  multiSelect: false
  options:
    - label: "Review code"
      description: "Run code review on files or a PR"
    - label: "Debug an issue"
      description: "Investigate and fix a bug"
    - label: "Refactor code"
      description: "Improve code structure"
    - label: "Commit changes"
      description: "Stage and commit current work"
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

## Behavior

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
