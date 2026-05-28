---
type: concept
name: plugin-concept
feature: plugin
depth: concept
generated_at: 2026-05-27T13:42:27.323011+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Plugin

The attune plugin is a collection of hooks, slash commands, and MCP configuration that runs inside Claude Code to maintain session continuity, enforce security boundaries, and surface workspace context at the right moment.

## Core responsibilities

The plugin operates through a set of focused entry points, each fired at a specific moment in the Claude Code lifecycle:

| Hook module | When it runs | What it does |
|---|---|---|
| `hooks.welcome` | Session start | Orients you to the current workspace |
| `hooks.spec_orient` | Session start | Summarizes in-flight specs from `~/attune` |
| `hooks.format_on_save` | File save | Runs the formatter on changed files |
| `hooks.compact_warning` | Context growth | Warns when transcript utilization approaches the limit |
| `hooks.help_on_error` | Tool error | Surfaces relevant help for the failing operation |
| `hooks.help_post_commit` | Git commit | Suggests next steps after a commit |
| `hooks.help_freshness_check` | Session start | Checks whether cached help content is stale |
| `hooks.security_guard` | Before tool use | Validates bash commands and file paths before execution |
| `hooks._handoff_cli` | `/handoff` command | Builds a handoff summary for session transitions |

## Mental model

Think of the plugin as a thin event bus between Claude Code and your workspace. Each hook reads shared state — git history, open specs, transcript size — and either blocks an action, emits a prompt insertion, or exits silently. No hook carries persistent state of its own; they all read from the same sources at fire time.

Two dataclasses carry that shared state:

- **`SpecInfo`** (`slug`, `path`, `layer`, `phase`, `status`, `mtime`) — represents one in-flight spec discovered under a workspace root. `discover_specs(roots)` walks `specs/` directories and returns a list of these.
- **`GitState`** (`branch`, `last_sha`, `last_subject`, `uncommitted`) — a snapshot of the worktree at the moment a hook fires. `git_state(cwd)` populates it.

A typical hook call looks like this:

1. `workspace_roots(cwd)` finds the workspace directories to scan.
2. `discover_specs(roots)` returns the current `SpecInfo` list.
3. `git_state(cwd)` returns the current `GitState`.
4. The hook formats output — for example, `build_resume_prompt(spec_info, git_state)` assembles the resume prompt body — and writes it to stdout or returns a allow/deny verdict.

## Context utilization and compact warnings

`estimate_utilization(transcript_path)` returns a float in `[0.0, 1.0]` representing how full the active transcript is. When that value crosses a threshold, `format_warning(util, threshold, resume_body)` composes a visible warning that includes the resume prompt so you can continue work in a fresh session without losing context.

The plugin uses sentinel files (see `session_sentinel_path`, `prune_stale_sentinels`) to ensure the warning appears at most once per session, not on every message after the threshold is crossed.

## Security boundary

`hooks.security_guard` runs before any bash or file-write tool call. `validate_bash_command(command)` rejects commands that target system directories listed in `SYSTEM_DIRECTORIES` (such as `/etc`, `/proc`, and `/sys`), while allowing read-only search prefixes in `SEARCH_COMMAND_PREFIXES` (such as `rg`, `git log`, and `git diff`). `validate_file_path(file_path)` applies the same directory list to write operations. Both return a `(allowed: bool, reason: str)` tuple that `main(context)` uses to either pass the tool call through or return a denial with an explanation.

## When this matters

The plugin is relevant when you are:

- **Resuming a session** — `spec_orient` and `welcome` fire at startup to rebuild context from `SpecInfo` and `GitState` rather than relying on transcript history.
- **Approaching the context limit** — `compact_warning` fires before Claude Code compacts automatically, giving you a structured resume prompt to carry forward.
- **Running potentially destructive commands** — `security_guard` intercepts tool calls and stops writes to system directories before they execute.
- **Handing off to another session** — the `/handoff` command via `_handoff_cli` produces a summary built from the same `SpecInfo` and `GitState` that the other hooks use.
