---
name: attune-test
description: "Generate tests for a module or file"
argument-hint: "<path to generate tests for>"
category: workflows
aliases: [atest]
tags: [test, generate, coverage, tdd]
version: "3.0.0"
---

# attune-test

Quick-access command to generate tests. Bypasses
Socratic discovery for when you know what you want.

## Execution

1. If a path argument is provided, use it. Otherwise
   ask: "Which module or file needs tests?"
2. Call the `test_generation` MCP tool with the path.
3. Present generated tests with edge cases and security
   test coverage.

## Examples

```
/attune-test src/attune/config.py
/attune-test src/attune/workflows/
/attune-test src/attune/models/provider_config.py
```
