---
type: warning
name: pytest-importorskip-triggers-ruff-e402
confidence: Verified
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# Warning: `pytest.importorskip` triggers ruff E402

## Condition

Test files that call `pytest.importorskip(...)` before optional imports cause ruff to flag those imports as E402 (module level import not at top of file)

## Risk

Ignoring this guidance may cause: `pytest.importorskip` triggers ruff E402

## Mitigation

1. add `# noqa: E402` to each import line after the `importorskip` call

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `pytest.importorskip` triggers ruff E402
