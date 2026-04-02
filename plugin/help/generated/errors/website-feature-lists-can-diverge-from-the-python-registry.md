---
type: error
name: website-feature-lists-can-diverge-from-the-python-registry
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Website feature lists can diverge from the Python registry

## Signature

Website feature lists can diverge from the Python registry

## Root Cause

The `/workflows` page had 14 manually-authored fictional workflows that didn't match `list_workflows()`. Always verify website feature claims against the live Python code before publishing.

## Resolution

1. Always verify website feature claims against the live Python code before publishing

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Website feature lists can diverge from the Python registry
