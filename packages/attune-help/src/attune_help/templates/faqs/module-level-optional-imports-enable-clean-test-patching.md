---
type: faq
name: module-level-optional-imports-enable-clean-test-patching
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: How do I handle module-level optional imports enable clean test patching?

## Answer

A local `import anthropic` inside a function body can't be patched with `unittest.mock.patch` because the name isn't bound at module scope. Move to module-level with an availability guard (`_anthropic = None`; `_ANTHROPIC_AVAILABLE = False`) and patch as `module._anthropic`.

```
import anthropic
```

## Related Topics
- **Error**: Detailed error: Module-level optional imports enable clean test patching
