---
type: warning
name: commands-are-not-namespaced-in-plugins-skills-are
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Commands are NOT namespaced in plugins, skills ARE

## Condition

A command named `attune` in `commands/attune.md` is invoked as `/attune` directly

## Risk

Ignoring this guidance may cause: Commands are NOT namespaced in plugins, skills ARE

## Mitigation

1. Check Claude Code built-ins (`/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`) before naming commands to avoid collisions

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Commands are NOT namespaced in plugins, skills ARE
