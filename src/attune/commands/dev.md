---
name: dev
description: Developer tools — debug, commit, PR, code review, refactoring
category: hub
aliases: [developer, d]
tags: [development, debug, commit, review, refactor]
version: "1.0.0"
question:
  header: "Developer Tools"
  question: "What do you need to do?"
  multiSelect: false
  options:
    - label: "Debug an issue"
      description: "Investigate errors, trace execution, find root causes"
    - label: "Review code"
      description: "Quality analysis, security review, performance review"
    - label: "Commit changes"
      description: "Stage, commit with conventional commit message"
    - label: "Create a PR"
      description: "Push branch, create pull request with description"
---

# dev

Developer tools hub — debug, commit, PR, code review, and refactoring.

## Quick Shortcuts

| Shortcut | Action |
| -------- | ------ |
| `/dev debug` | Start interactive debugging session |
| `/dev review` | Run code review workflow |
| `/dev review <path>` | Review specific file or directory |
| `/dev commit` | Stage and commit changes |
| `/dev pr` | Create a pull request |
| `/dev refactor` | Analyze and suggest refactoring |
| `/dev quality` | Run bug prediction analysis |

## Natural Language

Describe what you need:

- "debug the authentication error"
- "review my changes"
- "commit with a good message"
- "create a PR for this feature"
- "this function is too complex, refactor it"

## CRITICAL: Workflow Execution Instructions

**When this command is invoked with arguments, you MUST execute the workflow, not answer ad-hoc.**

### Context Gathering (ALWAYS DO FIRST)

Before executing any action below, gather current project context:

1. Run: `git status --short`
2. Run: `git log --oneline -5`
3. Run: `git branch --show-current`
4. Run: `git diff --cached --stat`

Use this context to inform your actions (e.g., which files changed, current branch, staged changes).

### Shortcut Routing (EXECUTE THESE)

| Input | Action |
| ----- | ------ |
| `/dev debug` | Run Debug wizard: gather error details → analyze root cause → decompose fix → preview → confirm |
| `/dev debug <description>` | Run Debug wizard with the described error |
| `/dev review` | `uv run attune workflow run code-review` |
| `/dev review <path>` | `uv run attune workflow run code-review --path <path>` |
| `/dev commit` | Use git to stage and commit with conventional commit format |
| `/dev pr` | Use gh to create a pull request with summary and test plan |
| `/dev refactor` | Run Refactor wizard: describe goal → analyze structure → decompose steps → preview → confirm |
| `/dev refactor <path>` | Run Refactor wizard for the specified file or module |
| `/dev quality` | `uv run attune workflow run bug-predict` |
| `/dev quality <path>` | `uv run attune workflow run bug-predict --path <path>` |

### Natural Language Routing (EXECUTE THESE)

| Pattern | Action |
| ------- | ------ |
| "debug", "fix", "error", "bug", "trace" | Run Debug wizard flow |
| "review", "quality", "analyze" | `uv run attune workflow run code-review` |
| "commit", "save", "stage" | Use git to stage and commit |
| "pr", "pull request", "merge" | Use gh to create pull request |
| "refactor", "clean up", "simplify" | Run Refactor wizard flow |
| "predict", "risky" | `uv run attune workflow run bug-predict` |

**IMPORTANT:** When arguments are provided, DO NOT just display documentation. EXECUTE the action.

### CLI Reference

```bash
uv run attune workflow run code-review --path <target>
uv run attune workflow run bug-predict --path <target>
```
