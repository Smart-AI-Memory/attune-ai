---
type: faq
name: attune-skill-names-must-not-collide-with-claude-code-built-in
tags: [claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about attune skill names must not collide with Claude Code built-in commands?

## Answer

Claude Code's built-in `/batch` command (parallel code changes) shadows any Attune skill named `batch`. The user types `/batch submit` expecting Attune's Batch API workflow but gets Claude Code's orchestrator instead.

```
 command (parallel code changes) shadows any Attune skill named
```

## Related Topics
- **Error**: Detailed error: Attune skill names must not collide with Claude Code built-in
  commands
