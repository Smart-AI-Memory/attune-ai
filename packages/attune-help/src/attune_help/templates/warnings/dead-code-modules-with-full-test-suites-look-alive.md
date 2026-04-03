---
type: warning
name: dead-code-modules-with-full-test-suites-look-alive
confidence: Verified
tags: [testing, imports, claude-code, python]
source: .claude/CLAUDE.md
---

# Warning: Dead code modules with full test suites look alive

## Condition

`socratic/embeddings/` had 240 lines of passing tests, clean exports in `__init__.py`, and conftest fixtures — but zero imports from any workflow, CLI, or MCP path

## Risk

Ignoring this guidance may cause: Dead code modules with full test suites look alive

## Mitigation

1. `socratic/embeddings/` had 240 lines of passing tests, clean exports in `__init__.py`, and conftest fixtures — but zero imports from any workflow, CLI, or MCP path

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Dead code modules with full test suites look alive
