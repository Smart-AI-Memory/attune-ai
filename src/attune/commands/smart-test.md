---
name: smart-test
description: "Find test gaps and generate tests for uncovered code."
argument-hint: "<path or module to test>"
---

Find test gaps and generate tests for `$ARGUMENTS`.

If no path was provided, ask the user what to test.

Use `uv run attune workflow run test-gen --path <target>`
to execute. Scope with AskUserQuestion first: target path,
test style (unit, integration, behavioral).
