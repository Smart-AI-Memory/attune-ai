---
type: concept
feature: plugin
depth: concept
generated_at: 2026-04-19T18:52:10.806945+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Plugin

## What it is

The plugin is a Claude Code extension that monitors development activity and responds with automatic formatting, help suggestions, and security validation. It operates through event hooks that trigger when you write files, start sessions, encounter command errors, or make git commits.

## Core components

The plugin consists of four main hook types:

**Post-tool hooks** respond after you use Claude's tools:
- Auto-format Python files after Write/Edit operations
- Suggest relevant help when Bash commands fail
- Maintain .help/ directory freshness after git commits

**Session hooks** activate when you start working:
- Check help template staleness on session start
- Display welcome messages

**Security validation** protects your system:
- `validate_bash_command()` screens commands against security policies
- `validate_file_path()` prevents access to system directories like `/etc` and `/proc`
- Returns `(True, '')` for allowed operations

## Runtime architecture

The plugin includes a bundled attune-ai core for standalone operation. This means it can run independently without requiring the full attune framework to be installed. Each hook operates as a separate entry point with its own `main()` function, allowing Claude Code to invoke specific behaviors based on the development event that occurred.

When you encounter command failures, the plugin reads PostToolUse payloads to determine whether help suggestions are appropriate. When you save Python files, it automatically formats them. When you commit changes, it checks whether your .help/ directory needs updates.
