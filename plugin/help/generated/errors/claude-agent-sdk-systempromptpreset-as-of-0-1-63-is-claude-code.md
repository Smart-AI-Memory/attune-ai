---
type: error
name: claude-agent-sdk-systempromptpreset-as-of-0-1-63-is-claude-code
confidence: Verified
source: .claude/CLAUDE.md
---

# Error: Claude-agent-sdk `SystemPromptPreset` (as of
  0.1.63) is Claude-Code-preset-only, not a vehicle
  for custom system prompts

## Signature

Claude-agent-sdk `SystemPromptPreset` (as of
  0.1.63) is Claude-Code-preset-only, not a vehicle
  for custom system prompts

## Root Cause

the name suggests "a preset for building system prompts" but the real schema is narrower: `type: Literal["preset"]`, `preset: Literal["claude_code"]` (only one acceptable value), `append: NotRequired[str]` to append text, `exclude_dynamic_sections: NotRequired[bool]` as an all-or-nothing toggle for the built-in preset's dynamic sections. For **custom** system prompts, pass a plain string to `ClaudeAgentOptions(system_prompt=...)` — that path is already cache-friendly since the string is static and `cwd=` is a tool-execution config field, not text injected into the prompt stream. No action needed to get cross-run cache hits when using string prompts; `SystemPromptPreset` only applies when building on top of the claude_code preset.

## Resolution

1. the name suggests "a preset for building system prompts" but the real schema is narrower: `type: Literal["preset"]`, `preset: Literal["claude_code"]` (only one acceptable value), `append: NotRequired[str]` to append text, `exclude_dynamic_sections: NotRequired[bool]` as an all-or-nothing toggle for the built-in preset's dynamic sections

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
