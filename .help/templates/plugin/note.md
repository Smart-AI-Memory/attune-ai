---
type: note
feature: plugin
depth: note
generated_at: 2026-04-14T15:24:00.977661+00:00
source_hash: 425438f8a3b30d1fa8fe22fd642b4949e74d5b601ad76231735d0c4c4d94f3e8
status: generated
---

# Note: plugin

## Context

The Claude Code plugin provides a runtime environment for extending the development assistant with hooks, security policies, and automation tools.

## Plugin architecture

The plugin system operates through hook-based automation that responds to development events. When you use tools like file editing or bash commands, the plugin can trigger post-processing actions automatically.

The plugin includes these core components:

- **Format hooks** — Automatically format Python files after write operations
- **Help system integration** — Check template freshness and suggest relevant help when commands fail
- **Security validation** — Validate bash commands and file paths against security policies
- **Git automation** — Maintain help documentation after commits

## Entry points

Each plugin module exposes a `main()` function as its primary entry point:

- `format_on_save.py` reads tool results from stdin and formats Python files
- `help_freshness_check.py` validates help template currency on session start
- `help_on_error.py` analyzes failed commands and suggests relevant documentation
- `help_post_commit.py` updates stale help content after git commits

The security guard module provides validation functions that return boolean success status with error messages:

- `validate_bash_command()` checks commands against security policies
- `validate_file_path()` validates file access patterns
- The main security function processes tool calls and returns permission status

## Security boundaries

The plugin enforces security policies through predefined constraints. It blocks access to system directories including `/etc`, `/sys`, `/proc`, `/dev`, `/boot`, and macOS equivalents in `/private`. Search commands like `grep`, `rg`, and `git` operations receive special handling for safe execution.

**Tags:** `plugin`, `claude-code`
