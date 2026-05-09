---
type: error
name: research-subagents-can-hallucinate-sdk-signatures-introspect
confidence: Verified
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# Error: Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it

## Signature

Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it

## Root Cause

the 6.2.0 planning research claimed `SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])` would work. The actual `claude_agent_sdk.types.SystemPromptPreset.__annotations__` is `{type: Literal["preset"], preset: Literal["claude_code"], append: NotRequired[str], exclude_dynamic_sections: NotRequired[bool]}` — a **boolean** toggle, not a list of section names, and wraps only Claude Code's built-in `"claude_code"` preset (no vehicle for custom system prompts). Verifying the shape via `import inspect; inspect.signature(obj)` + `.__annotations__` cost ~1 minute and saved an entire task's worth of misdirected code. Research agents can confabulate API shapes from documentation-style priors without importing the code. Pattern: before implementing any task that depends on an SDK symbol the research agent named, run a short introspection check (`hasattr`, `inspect.signature`, `__annotations__`) as the first step of that task — especially for typed-dict / kwarg-only classes where there's no constructor signature to catch mistakes at call-time.

## Resolution

1. the 6.2.0 planning research claimed `SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])` would work

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics

None generated yet.
