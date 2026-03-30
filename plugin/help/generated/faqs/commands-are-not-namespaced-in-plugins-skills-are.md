---
type: faq
name: commands-are-not-namespaced-in-plugins-skills-are
tags: [claude-code]
source: CLAUDE.md Lessons Learned
---

# FAQ: What is the issue with: Commands are NOT namespaced in plugins, skills ARE?

## Answer

A command named `attune` in `commands/attune.md` is invoked as `/attune` directly. A skill named `workflow-orchestration` is invoked as `/attune-ai:workflow-orchestration`.


**Fix:**

- Check Claude Code built-ins (`/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`) before naming commands to avoid collisions

```
commands/attune.md
```

## Related Topics
- **Error**: Detailed error: Commands are NOT namespaced in plugins, skills ARE
