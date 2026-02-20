---
name: attune-review
description: "Run a code review on your codebase"
argument-hint: "<path to review>"
category: workflows
aliases: [arev]
tags: [review, quality, code-review, analyze]
version: "2.10.4"
---

# attune-review

Quick-access command to run a code review. Bypasses
Socratic discovery for when you know what you want.

## Execution

1. If a path argument is provided, use it. Otherwise
   ask: "Which files or directory should I review?"
2. Call the `code_review` MCP tool with the path.
3. Present results using the format from the
   code-quality skill.

## Examples

```
/attune-review src/attune/workflows/
/attune-review src/
/attune-review src/attune/cli.py
```
