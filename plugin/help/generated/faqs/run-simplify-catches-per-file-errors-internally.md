---
type: faq
name: run-simplify-catches-per-file-errors-internally
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about _run_simplify catches per-file errors internally?

## Answer

The pipeline orchestrator's `_run_simplify()` wraps each file in its own try/except, so even if `SimplifyCodeWorkflow()` raises, the method returns normally. The outer caller sets `result.simplified = True` regardless.

```
_run_simplify()
```

## Related Topics
- **Error**: Detailed error: `_run_simplify` catches per-file errors internally
