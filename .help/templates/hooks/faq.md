---
type: faq
name: hooks-faq
feature: hooks
depth: faq
generated_at: 2026-08-20T13:06:14.232086+00:00
source_hash: 5aba5457cc740ed70cb22f0f6e950c97d47eeeac8faabd7f0a716459b548cb13
status: generated
---

# Hooks FAQ

## Where are the hooks the plugin actually runs?

Under `attune/hooks/scripts/` (e.g. `security_guard`,
`worktree_path_guard`, `lessons_reminder`), wired via the plugin's
`hooks.json`.

## How does a hook block a tool?

A `PreToolUse` script exits `2` to block and `0` to allow.

## Is there a Python API to register hooks in-process?

No — that engine was removed in v13.0.0. Attune ships hook
scripts and lets Claude Code fire them.

## What happens on malformed input?

Scripts fail open (exit `0`) so a hook bug never blocks a real
tool call.
