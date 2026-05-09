---
type: error
name: attune-help-re-exports-create-a-hidden-cross-package-dep-on
confidence: Verified
tags: [imports, packaging]
source: .claude/CLAUDE.md
---

# Error: `attune.help` re-exports create a hidden cross-package
  dep on `attune-author`

## Signature

`attune.help` re-exports create a hidden cross-package
  dep on `attune-author`

## Root Cause

`src/attune/help/__init__.py` does `from attune_author.generator import ...` at module level. This works in dev because `[tool.uv.sources]` resolves `attune-author` from the local workspace path, but a vanilla `pip install attune-ai` from PyPI will fail at import time unless `attune-author` is also published. Either publish `attune-author` to PyPI in lockstep with `attune-ai` releases, wrap the imports in try/except for graceful degradation, or inline the types back into `attune.help`.

## Resolution

1. `src/attune/help/__init__.py` does `from attune_author.generator import ...` at module level

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: `attune.help` re-exports create a hidden cross-package
  dep on `attune-author`
