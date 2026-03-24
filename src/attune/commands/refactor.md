---
name: refactor
description: "Code-level refactoring analysis and roadmap generation."
argument-hint: "<path to analyze>"
---

Analyze refactoring opportunities in `$ARGUMENTS`.

If no path was provided, ask the user what to refactor.

Use `uv run attune workflow run refactor-plan --path <target>`
to execute. Scope with AskUserQuestion first: target path,
focus (complexity reduction, extraction, tech debt).
