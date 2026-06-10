---
type: concept
name: plugin-concept
feature: plugin
depth: concept
generated_at: 2026-06-10T07:07:04.652645+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Plugin

The attune plugin is a collection of Claude Code hooks, slash commands, and MCP configuration that keeps an AI coding session oriented — tracking in-flight specs, monitoring context utilization, guarding against unsafe shell commands, and restoring session state across compactions.

## What the plugin does

Each hook fires at a specific point in a Claude Code session and has a narrow responsibility:

| Hook module | When it runs | What it does |
|---|---|---|
| `hooks.welcome` | Session start | Renders a welcome message |
| `hooks.session_recall` | Session start | Restores prior session context |
| `hooks.session_stash` | Session end | Persists session state for later recall |
| `hooks.jit_recall` | Decision points | Surfaces relevant rules from a curated decision-point map |
| `hooks.spec_orient` | On demand | Formats in-flight specs so the model stays oriented to active work |
| `hooks.compact_warning` | Context threshold | Warns when transcript utilization is high and embeds a resume prompt |
| `hooks.security_guard` | Before tool use | Validates bash commands and file paths against known-unsafe patterns |
| `hooks.format_on_save` | File save | Runs formatting on saved files |
| `hooks.help_freshness_check` | Periodic | Flags stale help content |
| `hooks.help_on_error` | On error | Surfaces relevant help for the error |
| `hooks.help_post_commit` | Post-commit | Delivers commit-specific guidance |

The `/handoff` slash command (`hooks._handoff_cli`) wraps the session handoff flow as a CLI entry point.

## Core data structures

Two dataclasses form the shared state that hooks read and write.

**`SpecInfo`** represents one in-flight spec discovered under a workspace root:

```
slug        str     — identifier used in cross-links
path        Path    — location on disk
layer       str     — architectural layer
phase       str     — lifecycle phase
status      str     — raw status from the spec header
mtime       float   — last-modified timestamp
effective_status  str   — resolved status after conflict detection
status_source     str   — 'header' or another source
status_conflict   bool  — True when header and inferred status disagree
```

**`GitState`** captures the worktree at the moment a hook fires:

```
branch          str            — current branch name
last_sha        str            — SHA of HEAD
last_subject    str            — subject line of HEAD commit
uncommitted     tuple[str, …]  — paths with uncommitted changes
```

## How the pieces fit together

`hooks._state` is the shared foundation. It exposes `discover_specs()`, which walks `specs/` and `docs/specs/` directories under each workspace root and returns a list of `SpecInfo` objects. It also exposes `git_state()`, which snapshots the current branch, HEAD commit, and uncommitted files into a `GitState`. Both data structures flow into other hooks as inputs.

`hooks.spec_orient` consumes a list of `SpecInfo` values and calls `format_orientation()` to produce a summary the model can read. For sessions that have been compacted, `render_spec_pin()` trims the output to a character budget so it fits in a post-compact context window.

`hooks.compact_warning` uses `estimate_utilization()` from `hooks._transcript_size` to measure how full the context window is (returned as a float in `[0.0, 1.0]`). When utilization crosses a threshold, `format_warning()` composes a warning that includes a resume prompt built by `build_resume_prompt()` from `hooks._resume_prompt`. The resume prompt draws on the current `SpecInfo` and `GitState` so the model can continue work after a compaction.

`hooks.security_guard` validates every bash command against `SEARCH_COMMAND_PREFIXES` and every file path against `SYSTEM_DIRECTORIES` before tool use proceeds. `validate_bash_command()` and `validate_file_path()` each return a `(bool, str)` tuple — the boolean indicates whether the operation is allowed, and the string carries the reason when it is not.

Session continuity across compactions relies on sentinel files. `session_sentinel_path()` returns the path for a per-session sentinel, and `prune_stale_sentinels()` removes sentinels older than the TTL, returning the count of files deleted.

## When this matters

The plugin is relevant whenever you need to understand why Claude Code behaves the way it does during a session — why a warning appeared, why a command was blocked, why the model described active specs at the start of a reply, or how context is preserved when the transcript is compacted. Each observable behavior maps to a specific hook and a specific function in `hooks._state`, `hooks._transcript_size`, or `hooks._resume_prompt`.
