---
type: faq
name: claude-agent-sdk-systempromptpreset-as-of-0-1-63-is-claude-code
source: .claude/CLAUDE.md
---

# FAQ: What should I know about claude-agent-sdk SystemPromptPreset (as of 0.1.63) is Claude-Code-preset-only, not a vehicle for custom system prompts?

## Answer

the name suggests "a preset for building system prompts" but the real schema is narrower: `type: Literal["preset"]`, `preset: Literal["claude_code"]` (only one acceptable value), `append: NotRequired[str]` to append text, `exclude_dynamic_sections: NotRequired[bool]` as an all-or-nothing toggle for the built-in preset's dynamic sections. For **custom** system prompts, pass a plain string to `ClaudeAgentOptions(system_prompt=...)` — that path is already cache-friendly since the string is static and `cwd=` is a tool-execution config field, not text injected into the prompt stream.

```
type: Literal["preset"]
```

## Related Topics
- **Error**: Detailed error: Claude-agent-sdk `SystemPromptPreset` (as of
  0.1.63) is Claude-Code-preset-only, not a vehicle
  for custom system prompts
