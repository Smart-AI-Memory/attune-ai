---
name: code-quality
description: "Code review and bug prediction — find quality issues, style violations, and likely bugs."
argument-hint: "<path or directory to review>"
---

Run a code review on `$ARGUMENTS`.

If no path was provided, ask the user what to review.

Use `uv run attune workflow run code-review --path <target>`
to execute. Scope with AskUserQuestion first: target path,
focus (security, quality, performance, or all).
