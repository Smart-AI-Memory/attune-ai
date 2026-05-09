---
type: warning
name: uv-run-in-pre-commit-hooks-propagates-lockfile-errors-as-hook
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: `uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated

## Condition

The `check-docs-freshness` hook uses `uv run python scripts/check_docs_freshness.py`

## Risk

sibling editable path missing in CI), the failure renders as "Check Help Template Freshness ..

## Mitigation

1. The `check-docs-freshness` hook uses `uv run python scripts/check_docs_freshness.py`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated
