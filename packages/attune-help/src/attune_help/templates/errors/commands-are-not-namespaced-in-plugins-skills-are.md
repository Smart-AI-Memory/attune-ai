---
type: error
name: commands-are-not-namespaced-in-plugins-skills-are
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Commands are NOT namespaced in plugins, skills ARE

## Signature

Commands are NOT namespaced in plugins, skills ARE

## Root Cause

A command named `attune` in `commands/attune.md` is invoked as `/attune` directly. A skill named `workflow-orchestration` is invoked as `/attune-ai:workflow-orchestration`. Keep a command as the short entry point when UX matters. Check Claude Code built-ins (`/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`) before naming commands to avoid collisions.

## Resolution

1. Check Claude Code built-ins (`/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`) before naming commands to avoid collisions

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Commands are NOT namespaced in plugins, skills ARE
