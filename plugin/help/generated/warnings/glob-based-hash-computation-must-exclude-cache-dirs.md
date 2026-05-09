---
type: warning
name: glob-based-hash-computation-must-exclude-cache-dirs
confidence: Verified
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# Warning: Glob-based hash computation must exclude cache dirs

## Condition

`compute_source_hash()` in `help/staleness.py` used `Path.glob("**/*")` which matched `__pycache__/*.pyc` and `.mypy_cache/*`

## Risk

Fix: filter paths through `_is_excluded()` which rejects any path containing `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules`, or `.git`

## Mitigation

1. filter paths through `_is_excluded()` which rejects any path containing `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules`, or `.git`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Glob-based hash computation must exclude cache dirs
