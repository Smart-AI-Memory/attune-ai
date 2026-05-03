---
name: dead-code-modules-with-full-test-suites-look-alive
source: .claude/CLAUDE.md
summary: This template explains how a module can have comprehensive passing tests
  and clean exports while still being dead code if nothing in the actual application
  imports or uses it.
tags:
- testing
- imports
- claude-code
- python
type: faq
---

# FAQ: Why Do Dead Code Modules With Full Test Suites Appear to Be Alive?

## Answer

A module can have 240 lines of passing tests, clean exports in `__init__.py`, and `conftest` fixtures — and still be completely dead. If nothing in your actual workflow, CLI, or MCP path ever imports it, those tests are validating code in isolation, not proving integration.

`socratic/embeddings/` is a concrete example of this pattern:

```
socratic/embeddings/
```

This directory had all the hallmarks of a healthy, active module. But a search across every workflow, CLI entry point, and MCP path revealed **zero imports**. The tests were passing because the tests themselves were the only callers.

**Passing tests are not evidence of integration.** They are evidence that the module behaves correctly when called — they say nothing about whether anything ever calls it in production.

## What To Watch For

- Modules with robust test coverage but no appearance in import graphs
- Well-structured `__init__.py` exports that nothing outside the module consumes
- `conftest` fixtures scoped to a subtree that no other test directory references

## Related Topics

- **Concept:** Distinguishing unit test coverage from integration coverage
- **Concept:** Using import graph analysis to identify unreachable code
- **Error:** Dead code modules with full test suites appear alive
