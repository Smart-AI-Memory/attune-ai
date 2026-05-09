---
type: warning
name: research-subagents-can-hallucinate-sdk-signatures-introspect
confidence: Verified
tags: [imports, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it

## Condition

the 6.2.0 planning research claimed `SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])` would work

## Risk

Ignoring this guidance may cause: Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it

## Mitigation

1. the 6.2.0 planning research claimed `SystemPromptPreset(exclude_dynamic_sections=["cwd", "git_status"])` would work

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Research subagents can hallucinate SDK signatures —
  introspect the real API before coding to it
