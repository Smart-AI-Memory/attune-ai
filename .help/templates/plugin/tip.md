---
type: tip
feature: plugin
depth: tip
generated_at: 2026-04-14T15:23:53.328755+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Use hooks for reactive behavior, not proactive tasks

## Context

Claude Code's plugin system includes six hooks that respond to specific events: format-on-save, help freshness checks, error suggestions, git commit maintenance, security validation, and session startup.

## Recommendation

Design your plugin extensions as event-driven hooks rather than polling or background processes. Each hook has a specific trigger (PostToolUse, SessionStart) and a focused responsibility.

Hooks excel at:
- Responding to user actions (`format_on_save.py` runs after Write/Edit tools)
- Maintaining consistency (`help_post_commit.py` updates help after git commits)
- Just-in-time validation (`security_guard.py` checks commands before execution)

## Why this works

Event-driven architecture keeps the plugin lightweight and responsive while ensuring actions happen at exactly the right moment in the user's workflow.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
