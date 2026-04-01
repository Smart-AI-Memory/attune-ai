---
type: warning
name: attune-skill-names-must-not-collide-with-claude-code-built-in
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Warning: Attune skill names must not collide with Claude Code built-in
  commands

## Condition

Claude Code's built-in `/batch` command (parallel code changes) shadows any Attune skill named `batch`

## Risk

Ignoring this guidance may cause: Attune skill names must not collide with Claude Code built-in
  commands

## Mitigation

1. Claude Code's built-in `/batch` command (parallel code changes) shadows any Attune skill named `batch`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Attune skill names must not collide with Claude Code built-in
  commands
