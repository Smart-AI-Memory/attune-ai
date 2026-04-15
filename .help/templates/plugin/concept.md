---
type: concept
feature: plugin
depth: concept
generated_at: 2026-04-14T15:22:21.269120+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Plugin

A Claude Code extension system that automatically executes actions at specific points in the development workflow through event-driven hooks.

## Hook-based architecture

The plugin system operates through event hooks that trigger when you perform specific actions:

- **SessionStart hooks** run when you begin a new Claude Code session
- **PostToolUse hooks** execute after Claude completes tool operations like writing files or running commands

Each hook is a standalone executable that receives event data and performs targeted actions. For example, when you save a Python file, the format-on-save hook automatically runs code formatting.

## Security validation

The security guard component validates commands and file paths before execution:

- `validate_bash_command()` checks shell commands against security policies, blocking access to system directories like `/etc`, `/sys`, and `/proc`
- `validate_file_path()` prevents operations on protected filesystem locations
- Returns validation results as `(allowed: bool, reason: str)` tuples

## Development workflow integration

The plugin system enhances your coding workflow through automated maintenance:

- **Code formatting**: Auto-formats Python files after Write/Edit operations
- **Help system maintenance**: Checks template freshness on session start and updates help content after git commits
- **Error assistance**: Suggests relevant help when Bash commands fail
- **Welcome messaging**: Displays startup information through stderr (visible in Claude Code interface)

The bundled runtime (attune-ai core) enables standalone plugin operation outside the main Claude Code process, ensuring plugins can run independently without blocking the primary interface.
