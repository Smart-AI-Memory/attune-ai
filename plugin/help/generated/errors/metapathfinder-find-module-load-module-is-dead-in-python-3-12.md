---
type: error
name: metapathfinder-find-module-load-module-is-dead-in-python-3-12
confidence: Verified
tags: [ci, testing, imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: MetaPathFinder `find_module`/`load_module` is dead in
  Python 3.12+ — use `sys.modules[name] = None` sentinel
  instead

## Signature

ImportError

## Root Cause

The existing "Verify optional dep boundaries with a MetaPathFinder" lesson is partially wrong. The deprecated `find_module` / `load_module` hooks stopped firing in 3.12's import machinery (which migrated to `find_spec`/`create_module`/`exec_module` fully). Tests using the old Blocker pattern fall through to the real SDK silently on 3.12+ CI matrix lanes. Cross-version replacement: `sys.modules[name] = None` — Python's import machinery treats the sentinel as "module is unavailable" and raises `ImportError` on the next `import name`. Works unchanged on 3.10-3.13. Remember to snapshot+restore the original `sys.modules` entries for the module and its dotted children.

## Resolution

1. The existing "Verify optional dep boundaries with a MetaPathFinder" lesson is partially wrong

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
