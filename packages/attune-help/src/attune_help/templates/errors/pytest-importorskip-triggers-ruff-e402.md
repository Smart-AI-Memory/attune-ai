---
type: error
name: pytest-importorskip-triggers-ruff-e402
confidence: Verified
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# Error: `pytest.importorskip` triggers ruff E402

## Signature

`pytest.importorskip` triggers ruff E402

## Root Cause

Test files that call `pytest.importorskip(...)` before optional imports cause ruff to flag those imports as E402 (module level import not at top of file).

## Resolution

1. add `# noqa: E402` to each import line after the `importorskip` call

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `pytest.importorskip` triggers ruff E402
- Task: Update test mocks and assertions
