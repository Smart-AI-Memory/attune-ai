---
type: concept
name: plugin-concept
feature: plugin
depth: concept
generated_at: 2026-06-11T04:47:10.944816+00:00
source_hash: bb1dd6bc42134bdd5537798d5887c1172d0c43bf4a6c4c2dc064f90213e6a7b3
status: generated
scaffold_hash: 3d3395b06e9c2911139c4e55ee7c889cc29a128f3757a3f2a936cdbc08cafd68
---

# Plugin

The attune-ai plugin extends Claude Code with a set of hooks, slash commands, skills, and MCP configuration that orient the AI within your workspace at key moments in a session.

## Session lifecycle and hooks

The plugin is organized as a collection of hooks, each bound to a specific event in the Claude Code session lifecycle. Understanding when each hook fires gives you a clear picture of what the plugin does and why.

At session start, `welcome.main()` displays workspace orientation and `session_recall.main()` restores context from the previous session. During a session, `jit_recall.main()` injects curated decision-point → rule mappings when the AI reaches a recognized decision point, and `compact_warning.main()` calls `estimate_utilization()` to warn you before context fills. Before any bash command executes, `security_guard.main()` calls `validate_bash_command()` and `validate_file_path()`, blocking writes to system directories such as `/etc`, `/sys`, and `/proc` listed in `SYSTEM_DIRECTORIES`. Commands whose first token appears in `SEARCH_COMMAND_PREFIXES` — for example, `grep`, `rg`, or `git log` — are treated as read-only and validated under more permissive rules. When you save a file, `format_on_save.main()` applies formatting. At session end, `session_stash.main()` persists state for the next session, and `_handoff_cli.main()` backs the `/handoff` slash command.

Two hooks serve the help system: `help_on_error.main()` surfaces relevant docs when a tool fails, and `help_post_commit.main()` together with `help_freshness_check.main()` flag stale help content after commits.

## Workspace state model

Most hooks share two dataclasses that describe the current workspace.

`SpecInfo` represents a single in-flight spec. Call `workspace_roots(cwd)` to locate the roots to scan, then pass the result to `discover_specs(roots)`, which walks the `specs/` and `docs/specs/` subdirectories and returns one `SpecInfo` per file. Each record carries a `slug`, `path`, `layer`, `phase`, `status`, and `mtime`. The derived `effective_status` field resolves any conflict between the spec's own header status and an external override; `status_conflict` is `True` when they disagree. A spec is considered terminal when `effective_status` matches one of the `_TERMINAL_VERDICTS` values — for example, `"shipped"`, `"done"`, or `"superseded"` — and still active when it matches an `_ONGOING_VERDICTS` value such as `"living"` or `"ongoing"`.

`GitState` is a lightweight snapshot of the worktree at hook-fire time. `git_state(cwd)` returns the current `branch`, the `last_sha` and `last_subject` of the most recent commit, and a `tuple` of `uncommitted` file paths.

`build_resume_prompt(spec_info, git_state)` combines both into the standard resume-prompt body used by session-boundary hooks. You can pass an optional `todo_summary` and set `workspace_path` (default `~/attune`) to match your layout.

## SDK subprocess gating

When attune-ai invokes Claude Code through the Agent SDK, it spawns a `claude` subprocess. Interactive hooks must not fire in that context — the output is invisible to you and can interfere with the parent session.

`is_sdk_subprocess()` detects this condition. Any hook that should self-gate calls `exit_if_sdk_subprocess()` at startup; the call silently exits with code 0 when the subprocess condition is true, leaving the parent session undisturbed. This pattern lets every hook share a single detection path without duplicating logic.

## Public interfaces

Other parts of the codebase interact with the plugin through these interfaces:

| Interface | Purpose | Module |
|-----------|---------|--------|
| `SpecInfo` | One in-flight spec discovered under a workspace root | `hooks._state` |
| `GitState` | Snapshot of the worktree's git state at hook-fire time | `hooks._state` |
| `discover_specs` | Walks workspace roots and returns all in-flight `SpecInfo` records | `hooks._state` |
| `build_resume_prompt` | Renders the standard resume-prompt body from workspace state | `hooks._resume_prompt` |
| `validate_bash_command` | Returns `(allowed, reason)` for a proposed bash command | `hooks.security_guard` |
| `validate_file_path` | Returns `(allowed, reason)` for a proposed file path | `hooks.security_guard` |
| `is_sdk_subprocess` | Returns `True` when running inside an SDK-spawned subprocess | `hooks._sdk_gate` |
