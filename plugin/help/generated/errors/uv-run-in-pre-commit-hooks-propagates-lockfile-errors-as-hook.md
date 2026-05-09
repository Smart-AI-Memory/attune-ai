---
type: error
name: uv-run-in-pre-commit-hooks-propagates-lockfile-errors-as-hook
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: `uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated

## Signature

`uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated

## Root Cause

The `check-docs-freshness` hook uses `uv run python scripts/check_docs_freshness.py`. When the lockfile has an unresolvable dep (e.g. sibling editable path missing in CI), the failure renders as "Check Help Template Freshness ... Failed" with a metadata-resolution traceback in the log — nothing about docs or templates. When seemingly-unrelated pre-commit hooks start failing, read the actual log and check `uv.lock` resolvability before assuming the hook's nominal responsibility is the issue.

## Resolution

1. The `check-docs-freshness` hook uses `uv run python scripts/check_docs_freshness.py`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `uv run` in pre-commit hooks propagates lockfile
  errors as hook failures that look unrelated
