---
type: faq
name: dead-code-modules-with-full-test-suites-look-alive
tags: [testing, imports, claude-code, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about dead code modules with full test suites look alive?

## Answer

`socratic/embeddings/` had 240 lines of passing tests, clean exports in `__init__.py`, and conftest fixtures — but zero imports from any workflow, CLI, or MCP path. Tests passing is not evidence of integration.

```
socratic/embeddings/
```

## Related Topics
- **Error**: Detailed error: Dead code modules with full test suites look alive
