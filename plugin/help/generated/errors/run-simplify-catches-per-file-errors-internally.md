---
type: error
name: run-simplify-catches-per-file-errors-internally
confidence: Verified
tags: [testing, packaging]
source: .claude/CLAUDE.md
---

# Error: `_run_simplify` catches per-file errors internally

## Signature

`_run_simplify` catches per-file errors internally

## Root Cause

The pipeline orchestrator's `_run_simplify()` wraps each file in its own try/except, so even if `SimplifyCodeWorkflow()` raises, the method returns normally. The outer caller sets `result.simplified = True` regardless. Tests must match this behavior — the outer try/except only fires if `_run_simplify` itself raises, not if individual files fail.

## Resolution

1. The pipeline orchestrator's `_run_simplify()` wraps each file in its own try/except, so even if `SimplifyCodeWorkflow()` raises, the method returns normally

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
