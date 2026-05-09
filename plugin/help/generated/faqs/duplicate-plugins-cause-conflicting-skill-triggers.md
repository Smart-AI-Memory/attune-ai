---
type: faq
name: duplicate-plugins-cause-conflicting-skill-triggers
tags: [testing, security, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about duplicate plugins cause conflicting skill triggers?

## Answer

Having both `attune-lite` and `attune-ai` installed creates duplicate skills (`security-audit`, `smart-test`, etc.). Claude sees both and must pick one, degrading UX.

```
attune-lite
```

## Related Topics
- **Error**: Detailed error: Duplicate plugins cause conflicting skill triggers
