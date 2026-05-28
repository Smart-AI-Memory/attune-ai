---
type: comparison
name: plugin-comparison
feature: plugin
depth: comparison
generated_at: 2026-05-27T13:42:27.354756+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Comparison: Plugin hooks vs direct scripting

## Context

The plugin ships a suite of lifecycle hooks for Claude Code — session handoff, compact warnings, security validation, spec orientation, and post-commit help. Each hook is a standalone entry point backed by shared state helpers in `hooks._state`. This page helps you decide when to use the plugin's hooks and when a simpler approach is the better fit.

## Hook-by-hook summary

| Hook module | Entry point | What it does | Requires git? |
|---|---|---|---|
| `hooks._handoff_cli` | `main() -> int` | Drives the `/handoff` slash command | Yes — reads `GitState` |
| `hooks._resume_prompt` | `build_resume_prompt(...)  -> str` | Renders the session-resume prompt with spec and git context | Yes |
| `hooks.compact_warning` | `main() -> int` | Emits a context-utilization warning when `estimate_utilization()` exceeds a threshold | No |
| `hooks.format_on_save` | `main() -> None` | Runs the formatter on save events | No |
| `hooks.help_freshness_check` | `main() -> None` | Checks whether help content is stale | No |
| `hooks.help_on_error` | `main() -> None` | Surfaces contextual help after an error | No |
| `hooks.help_post_commit` | `main() -> None` | Surfaces help after a commit | Yes |
| `hooks.security_guard` | `main(context) -> dict` | Validates bash commands and file paths before execution | No |
| `hooks.spec_orient` | `main() -> int` | Formats and pins the active spec for the current session | Yes |
| `hooks.welcome` | `main() -> None` | Runs once at session start | No |

## Plugin hooks vs a throwaway script

| Criterion | Plugin hook | Throwaway script |
|---|---|---|
| **State discovery** | `discover_specs()` + `workspace_roots()` handle multi-root workspaces automatically | You must locate and parse spec files manually |
| **Git context** | `git_state(cwd)` returns branch, last SHA, last subject, and uncommitted files in one call | You shell out to `git` and parse the output yourself |
| **Session continuity** | `session_sentinel_path()` and `prune_stale_sentinels()` manage once-per-session deduplication | You implement your own sentinel logic |
| **Context utilization** | `estimate_utilization(transcript_path)` returns a `[0.0, 1.0]` float ready to threshold | You compute transcript size and derive a ratio manually |
| **Security validation** | `validate_bash_command()` and `validate_file_path()` check against `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES` | You replicate or skip the allow/deny logic |
| **Prompt rendering** | `build_resume_prompt()` composes spec info, git state, workspace path, and todo summary into a single string | You template the prompt yourself |
| **Maintenance** | Hooks evolve with the plugin; your callers get fixes automatically | Each script is independent and drifts separately |
| **Best for** | Persistent, production-grade Claude Code integrations | One-off investigation or a feature not yet in the API |

The plugin hooks are clearly the stronger choice for anything that runs regularly. A throwaway script is reasonable for exploratory work — but once you find yourself re-implementing `git_state()` or sentinel management, that is a signal to switch.

## Plugin hooks vs calling Claude Code directly (no hooks)

Without the hooks layer, Claude Code has no automatic access to:

- In-flight spec metadata (`SpecInfo`: `slug`, `layer`, `phase`, `status`, `mtime`)
- Workspace root discovery across multiple directories
- Compact warnings tied to real transcript utilization
- Session-scoped deduplication of warnings and orientation prompts

If you skip the hooks, you lose these capabilities entirely — they are not duplicated elsewhere in the plugin's public API.

## Use the plugin hooks when…

- **You need session continuity.** `session_sentinel_path()` and `prune_stale_sentinels()` keep once-per-session behaviour correct without manual bookkeeping.
- **You are working in a multi-root workspace.** `workspace_roots()` and `discover_specs()` handle the traversal; a script cannot match this without replicating the logic.
- **You need git context reliably.** `git_state(cwd)` returns a typed `GitState` dataclass — branch, last SHA, last subject, and uncommitted files — rather than fragile shell output parsing.
- **You are building a security boundary.** `validate_bash_command()` and `validate_file_path()` enforce the `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES` allow/deny rules that you would otherwise have to maintain yourself.
- **You are rendering a resume or orientation prompt.** `build_resume_prompt()` and `format_orientation()` produce consistent output; hand-rolled prompts diverge over time.

## Skip the plugin hooks when…

- Your task is purely exploratory and you do not plan to run it more than once or twice.
- The behaviour you need is not exposed by the public API — in that case, file an issue or propose an extension point rather than patching internals.
- Your integration lives at the orchestration layer above the plugin; in that case, call the orchestration API rather than individual hooks directly.

**Tags:** `plugin`, `claude-code`
