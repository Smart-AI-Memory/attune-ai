---
type: error
name: dead-code-modules-with-full-test-suites-look-alive
confidence: Verified
tags: [testing, imports, claude-code, python]
source: .claude/CLAUDE.md
---

# Error: Dead code modules with full test suites look alive

## Signature

Dead code modules with full test suites look alive

## Root Cause

`socratic/embeddings/` had 240 lines of passing tests, clean exports in `__init__.py`, and conftest fixtures — but zero imports from any workflow, CLI, or MCP path. Tests passing is not evidence of integration. Grep for imports outside the module itself before considering a feature "active".

## Resolution

1. Grep for imports outside the module itself before considering a feature "active"

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
