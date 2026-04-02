---
type: warning
name: website-feature-lists-can-diverge-from-the-python-registry
confidence: Verified
source: .claude/CLAUDE.md
---

# Warning: Website feature lists can diverge from the Python registry

## Condition

The `/workflows` page had 14 manually-authored fictional workflows that didn't match `list_workflows()`

## Risk

Ignoring this guidance may cause: Website feature lists can diverge from the Python registry

## Mitigation

1. Always verify website feature claims against the live Python code before publishing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Website feature lists can diverge from the Python registry
