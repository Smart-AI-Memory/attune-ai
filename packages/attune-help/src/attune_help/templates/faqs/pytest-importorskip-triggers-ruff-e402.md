---
type: faq
name: pytest-importorskip-triggers-ruff-e402
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about pytest.importorskip triggers ruff E402?

## Answer

Test files that call `pytest.importorskip(...)` before optional imports cause ruff to flag those imports as E402 (module level import not at top of file). The pattern is intentional and correct — ruff just can't see the skip logic.

**How to fix:**
- add `# noqa: E402` to each import line after the `importorskip` call

```
pytest.importorskip(...)
```

## Related Topics
- **Error**: Detailed error: `pytest.importorskip` triggers ruff E402
