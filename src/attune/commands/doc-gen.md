---
name: doc-gen
description: "Generate documentation from source code — docstrings, README sections, API references."
argument-hint: "<path or module to document>"
---

Generate documentation for `$ARGUMENTS`.

If no path was provided, ask the user what to document.

Use `uv run attune workflow run doc-gen --path <target>`
to execute. Scope with AskUserQuestion first: target path,
doc type (API reference, README, module overview).
