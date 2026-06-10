---
type: faq
name: plugin-faq
feature: plugin
depth: faq
generated_at: 2026-06-10T07:07:04.679170+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Plugin FAQ

## What is the plugin?

The plugin is attune's Claude Code integration — it bundles skills, hooks, slash commands, and MCP configuration that Claude Code needs to work with attune workspaces.

## What hooks does the plugin provide?

Each hook is an independent entry point with its own `main()` function:

| Module | What it does |
|---|---|
| `hooks.compact_warning` | Warns when context utilization (via `estimate_utilization`) exceeds a threshold and injects a resume prompt |
| `hooks.format_on_save` | Runs formatting when a file is saved |
| `hooks.help_freshness_check` | Checks whether help content is stale |
| `hooks.help_on_error` | Surfaces help content when an error occurs |
| `hooks.help_post_commit` | Surfaces help content after a commit |
| `hooks.jit_recall` | Just-in-time recall of relevant rules at decision points |
| `hooks.security_guard` | Validates bash commands and file paths before execution |
| `hooks.session_recall` | Restores session context at the start of a session |
| `hooks.session_stash` | Saves session context when a session ends |
| `hooks.spec_orient` | Summarizes in-flight specs to orient Claude at session start |
| `hooks.welcome` | Runs on first connection to greet and orient Claude |
| `hooks._handoff_cli` | CLI wrapper for the `/handoff` slash command |

## How does the plugin know which specs are in flight?

`discover_specs(roots)` in `hooks._state` walks `specs/` and `docs/specs/` directories under each workspace root and returns a list of `SpecInfo` objects. Each `SpecInfo` carries the spec's `slug`, `path`, `layer`, `phase`, `status`, `mtime`, `effective_status`, `status_source`, and `status_conflict` fields. Call `workspace_roots()` first if you don't already have a list of roots.

## How does the plugin decide a spec is "done"?

It compares `effective_status` against the terminal verdicts `{'closed', 'complete', 'completed', 'retired', 'superseded', 'shipped', 'done'}`. Any spec whose status matches one of those values is treated as finished and excluded from active orientation output.

## What does `security_guard` actually check?

`validate_bash_command(command)` blocks commands that touch system directories such as `/etc`, `/sys`, `/proc`, and `/dev`. `validate_file_path(file_path)` checks the target path against the same set of protected locations. Both functions return a `(bool, str)` tuple — `True` with an empty message means the input is allowed; `False` means it was blocked, and the string explains why.

## How does compact warning decide when to fire?

`estimate_utilization(transcript_path)` returns a float in `[0.0, 1.0]` representing how full the context window is. `format_warning(util, threshold, resume_body)` composes the warning message only when `util` exceeds `threshold`. The resume body is built by `build_resume_prompt()` in `hooks._resume_prompt`.

## How do I build the resume prompt myself?

Call `build_resume_prompt(spec_info, git_state, workspace_path=..., todo_summary=...)` from `hooks._resume_prompt`. Pass a `SpecInfo` (or `None` if there is no active spec) and a `GitState` snapshot from `hooks._state.git_state(cwd)`. The function returns a formatted string ready to inject into a prompt.

## What git information does the plugin capture?

`git_state(cwd)` returns a `GitState` with four fields: `branch`, `last_sha`, `last_subject`, and `uncommitted` (a tuple of changed file paths). The plugin uses this snapshot in resume prompts and handoff output.

## What are session sentinels, and why do they exist?

A session sentinel is a file whose presence tells `jit_recall` that it has already fired once in the current session, preventing duplicate recalls. `session_sentinel_path(session_id)` returns the path for a given session. `prune_stale_sentinels()` deletes sentinel files older than the TTL and returns the count of files removed.

## Where are the source files?

All hook modules live under `plugin/**`. The shared state helpers (`SpecInfo`, `GitState`, `discover_specs`, `git_state`, `workspace_roots`, and the sentinel functions) are in `hooks._state`.

**Tags:** `plugin`, `claude-code`
