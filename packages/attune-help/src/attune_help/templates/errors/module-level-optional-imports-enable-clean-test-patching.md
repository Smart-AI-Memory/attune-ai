---
type: error
name: module-level-optional-imports-enable-clean-test-patching
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Error: Module-level optional imports enable clean test patching

## Signature

Module-level optional imports enable clean test patching

## Root Cause

A local `import anthropic` inside a function body can't be patched with `unittest.mock.patch` because the name isn't bound at module scope. Move to module-level with an availability guard (`_anthropic = None`; `_ANTHROPIC_AVAILABLE = False`) and patch as `module._anthropic`. This is the established pattern in adapters (YAML guard) — apply it to any optional SDK dependency.

## Resolution

1. Move to module-level with an availability guard (`_anthropic = None`; `_ANTHROPIC_AVAILABLE = False`) and patch as `module._anthropic`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: Module-level optional imports enable clean test patching
- Task: Update test mocks and assertions
