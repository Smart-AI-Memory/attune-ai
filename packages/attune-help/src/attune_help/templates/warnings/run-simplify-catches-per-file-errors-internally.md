---
type: warning
name: run-simplify-catches-per-file-errors-internally
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Warning: `_run_simplify` catches per-file errors internally

## Condition

The pipeline orchestrator's `_run_simplify()` wraps each file in its own try/except, so even if `SimplifyCodeWorkflow()` raises, the method returns normally

## Risk

Tests must match this behavior — the outer try/except only fires if `_run_simplify` itself raises, not if individual files fail

## Mitigation

1. The pipeline orchestrator's `_run_simplify()` wraps each file in its own try/except, so even if `SimplifyCodeWorkflow()` raises, the method returns normally

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `_run_simplify` catches per-file errors internally
