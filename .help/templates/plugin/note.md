---
type: note
feature: plugin
depth: note
generated_at: 2026-04-19T18:53:51.789608+00:00
source_hash: cc66c32b53d43302658abed13a290caa83674b971790b41324cfbf01e8b7773b
status: generated
---

# Note: plugin

## Context

The Claude Code plugin is a collection of automation hooks and security controls that run alongside coding sessions. It provides automatic code formatting, help system maintenance, error assistance, and command validation.

## Design decisions

The plugin architecture uses standalone entry points rather than a class-based design. Each hook runs as an independent process that reads input from stdin or environment variables and performs one specific task:

- **PostToolUse hooks** run after Claude executes tools like Write or Edit files
- **SessionStart hooks** run when a new coding session begins
- **Security validation** happens before potentially dangerous commands execute

This process-based approach keeps hooks isolated and prevents one failing hook from affecting others.

## Core capabilities

The plugin bundle includes five main automation areas:

**Code formatting** — The `format_on_save` hook automatically runs Python formatters after file edits, ensuring consistent style without manual intervention.

**Help freshness** — Two hooks maintain the help system: `help_freshness_check` validates template currency when sessions start, while `help_post_commit` updates help content after git commits.

**Error assistance** — The `help_on_error` hook monitors bash command failures and suggests relevant help templates when users hit common problems.

**Security controls** — The `security_guard` module validates file paths and bash commands against policy rules, blocking access to system directories like `/etc` and `/proc`.

**Welcome messaging** — Session startup includes a brief welcome that appears in Claude Code's stderr panel.

All hooks share the same version (`6.2.0`) and operate on the attune-ai core runtime for consistency across different plugin environments.
