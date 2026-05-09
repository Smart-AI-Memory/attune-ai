---
type: warning
name: repo-root-parents-count-varies-by-file-depth
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: `_repo_root()` parents count varies by file depth

## Condition

A utility function using `Path(__file__).resolve().parents[N]` to find the repo root must match the file's actual depth

## Risk

Off-by-one silently resolves to `src/` instead of the repo root

## Mitigation

1. Always count: file → parent dir → ..

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `_repo_root()` parents count varies by file depth
