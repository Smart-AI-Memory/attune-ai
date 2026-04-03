---
type: error
name: claude-code-plugin-is-platform-specific
confidence: Verified
tags: [claude-code]
source: .claude/CLAUDE.md
---

# Error: Claude Code plugin is platform-specific

## Signature

Claude Code plugin is platform-specific

## Root Cause

Skills, hooks, and MCP config only work in Claude Code (CLI). They do not function in Claude.ai (web). When submitting to Anthropic's marketplace, scope the platform to Claude Code only — not "both platforms".

## Resolution

1. Skills, hooks, and MCP config only work in Claude Code (CLI)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: Claude Code plugin is platform-specific
