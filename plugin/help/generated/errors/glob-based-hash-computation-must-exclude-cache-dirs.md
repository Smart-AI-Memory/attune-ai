---
type: error
name: glob-based-hash-computation-must-exclude-cache-dirs
confidence: Verified
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# Error: Glob-based hash computation must exclude cache dirs

## Signature

Glob-based hash computation must exclude cache dirs

## Root Cause

`compute_source_hash()` in `help/staleness.py` used `Path.glob("**/*")` which matched `__pycache__/*.pyc` and `.mypy_cache/*`. Since bytecode files change between runs, the hash was non-deterministic — staleness detection flip-flopped between stale and fresh on consecutive calls.

## Resolution

1. filter paths through `_is_excluded()` which rejects any path containing `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules`, or `.git`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Glob-based hash computation must exclude cache dirs
- Task: Update test mocks and assertions
