---
type: concept
name: plugin-concept
feature: plugin
depth: concept
generated_at: 2026-05-21T03:20:39.390756+00:00
source_hash: 5586c41f1c99c9715bfc73d5dc9622c7133d156e10d5ec551da7c26153748cf1
status: generated
---

# Plugin

The Claude Code plugin provides a bundled runtime environment that enables standalone plugin operation with session continuity, state tracking, and context management.

## Core architecture

The plugin consists of four interconnected systems:

- **Command interface** — CLI wrapper that handles `/handoff` slash commands and routes them through the plugin runtime
- **Session continuity** — State discovery helpers that track workspace changes and maintain context across sessions
- **Resume prompt system** — Single source of truth for generating structured prompts that preserve session state
- **Context monitoring** — Transcript size estimation to prevent context overflow during long sessions

## State tracking model

The plugin maintains awareness of your development environment through two key data structures:

**`SpecInfo`** captures in-flight specifications discovered in your workspace:
- Spec location and metadata (path, layer, phase)
- Current status and last modification time
- Hierarchical organization under workspace roots

**`GitState`** provides a snapshot of version control state:
- Current branch and last commit details
- Uncommitted file inventory for session restoration
- Change tracking for intelligent prompt building

## Session continuity workflow

When you start a new session, the plugin:

1. Scans workspace roots to discover active specifications
2. Captures current git state including uncommitted changes
3. Estimates context utilization from previous transcripts
4. Builds a resume prompt with relevant state information
5. Warns if context usage approaches limits

This workflow ensures each session begins with full awareness of your project state, eliminating the need to re-explain context or lose track of in-progress work.

## Integration points

The plugin integrates with your development workflow through:
- **MCP configuration** for Claude Desktop integration
- **Workspace detection** that identifies project boundaries
- **Sentinel file management** for once-per-session warnings
- **Context utilization tracking** across transcript boundaries
