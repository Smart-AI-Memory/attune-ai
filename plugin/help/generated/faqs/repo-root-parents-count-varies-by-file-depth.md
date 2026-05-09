---
type: faq
name: repo-root-parents-count-varies-by-file-depth
source: .claude/CLAUDE.md
---

# FAQ: What should I know about _repo_root() parents count varies by file depth?

## Answer

A utility function using `Path(__file__).resolve().parents[N]` to find the repo root must match the file's actual depth. `src/attune/help/engine.py` needs `parents[3]` but `src/attune/workflows/help_maintenance.py` also needs `parents[3]` (not `parents[2]`).

**How to fix:**
- Always count: file → parent dir → ..

```
Path(__file__).resolve().parents[N]
```

## Related Topics
- **Error**: Detailed error: `_repo_root()` parents count varies by file depth
