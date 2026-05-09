---
type: error
name: repo-root-parents-count-varies-by-file-depth
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: `_repo_root()` parents count varies by file depth

## Signature

`_repo_root()` parents count varies by file depth

## Root Cause

A utility function using `Path(__file__).resolve().parents[N]` to find the repo root must match the file's actual depth. `src/attune/help/engine.py` needs `parents[3]` but `src/attune/workflows/help_maintenance.py` also needs `parents[3]` (not `parents[2]`). Always count: file → parent dir → ... → repo root. Off-by-one silently resolves to `src/` instead of the repo root.

## Resolution

1. Always count: file → parent dir → ..

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `_repo_root()` parents count varies by file depth
