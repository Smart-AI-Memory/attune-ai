---
type: faq
name: glob-based-hash-computation-must-exclude-cache-dirs
tags: [testing, imports, python]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about glob-based hash computation must exclude cache dirs?

## Answer

`compute_source_hash()` in `help/staleness.py` used `Path.glob("**/*")` which matched `__pycache__/*.pyc` and `.mypy_cache/*`. Since bytecode files change between runs, the hash was non-deterministic — staleness detection flip-flopped between stale and fresh on consecutive calls.

**How to fix:**
- filter paths through `_is_excluded()` which rejects any path containing `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `node_modules`, or `.git`

```
compute_source_hash()
```

## Related Topics
- **Error**: Detailed error: Glob-based hash computation must exclude cache dirs
