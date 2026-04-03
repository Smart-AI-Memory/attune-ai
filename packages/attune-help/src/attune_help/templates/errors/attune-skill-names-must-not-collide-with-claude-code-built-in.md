---
type: error
name: attune-skill-names-must-not-collide-with-claude-code-built-in
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Attune skill names must not collide with Claude Code built-in
  commands

## Signature

Attune skill names must not collide with Claude Code built-in
  commands

## Root Cause

Claude Code's built-in `/batch` command (parallel code changes) shadows any Attune skill named `batch`. The user types `/batch submit` expecting Attune's Batch API workflow but gets Claude Code's orchestrator instead. Renamed to `/bulk` to avoid the collision. When naming new skills, check Claude Code's built-in slash commands first: `/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`.

## Resolution

1. Claude Code's built-in `/batch` command (parallel code changes) shadows any Attune skill named `batch`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Attune skill names must not collide with Claude Code built-in
  commands
- Tip: Best practice: Attune skill names must not collide with Claude Code built-in
  commands
