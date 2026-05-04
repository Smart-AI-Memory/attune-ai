---
type: concept
feature: plugin
depth: concept
generated_at: 2026-05-04T02:38:26.322979+00:00
source_hash: b0ee9918b90b55b1b86413bf2ab78f0a590fb78eae098da3ba2886258d9db841
status: generated
---

# Plugin

The plugin system provides automated assistance during your Claude Code sessions through event-driven hooks and security validation.

## Core capabilities

The plugin system operates through five specialized hooks that respond to specific events:

**Code formatting** — Automatically formats Python files after you use Write or Edit tools, keeping your code style consistent without manual intervention.

**Help maintenance** — Checks help template freshness when sessions start and suggests relevant help content when Bash commands fail, ensuring you have current guidance.

**Repository awareness** — Detects stale help content after git commits and prompts updates, keeping documentation synchronized with code changes.

**Security validation** — Validates Bash commands and file paths against security policies before execution, preventing access to system directories like `/etc`, `/sys`, and `/proc`.

## Event-driven architecture

The plugin system uses hooks that trigger automatically:

| Hook type | When it runs | What it does |
|-----------|--------------|--------------|
| **PostToolUse** | After Write/Edit tools | Formats Python files with standard style |
| **SessionStart** | When Claude Code session begins | Checks help template freshness |
| **PostToolUse** | After Bash commands fail | Suggests relevant help content |
| **PostToolUse** | After git commits | Detects and flags stale help |

## Security boundaries

The security system maintains a whitelist approach — commands and paths are validated against known-safe patterns. Search commands like `grep`, `rg`, and `git grep` are permitted, while access to system directories is blocked.

The validation functions return simple boolean results: either a command is allowed (`True, ''`) or blocked with an explanation. This keeps the security model predictable and transparent.

## Bundled runtime

The plugin includes the attune-ai core as a bundled runtime, enabling standalone operation without external dependencies. This ensures consistent behavior across different development environments and eliminates version conflicts with system-wide installations.
