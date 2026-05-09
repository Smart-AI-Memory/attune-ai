---
type: faq
name: research-subagents-can-hallucinate-sdk-signatures-introspect
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about research subagents can hallucinate SDK signatures — introspect the real API before coding to it?

## Answer

the 6.2.0 planning research claimed `SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])` would work. The actual `claude_agent_sdk.types.SystemPromptPreset.__annotations__` is `{type: Literal["preset"], preset: Literal["claude_code"], append: NotRequired[str], exclude_dynamic_sections: NotRequired[bool]}` — a **boolean** toggle, not a list of section names, and wraps only Claude Code's built-in `"claude_code"` preset (no vehicle for custom system prompts).

```
SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])
```

## Related Topics
- **Error**: Detailed error: Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it
