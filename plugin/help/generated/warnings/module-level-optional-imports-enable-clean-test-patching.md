---
type: warning
name: module-level-optional-imports-enable-clean-test-patching
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: Module-level optional imports enable clean test patching

## Condition

A local `import anthropic` inside a function body can't be patched with `unittest.mock.patch` because the name isn't bound at module scope

## Risk

Ignoring this guidance may cause: Module-level optional imports enable clean test patching

## Mitigation

1. Move to module-level with an availability guard (`_anthropic = None`; `_ANTHROPIC_AVAILABLE = False`) and patch as `module._anthropic`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Module-level optional imports enable clean test patching
