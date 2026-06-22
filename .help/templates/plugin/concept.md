---
type: concept
name: plugin-concept
feature: plugin
depth: concept
generated_at: 2026-06-22T10:00:48.764701+00:00
source_hash: 843f895eed3fa2d3d0b8021830c8c31e3c292c176a967396a76c27deb5a60deb
status: generated
scaffold_hash: 41c8ef7e7320fa5ba02ff6bb2c51cab36592879c3e7ac3505bbb510d6b91be64
---

# Plugin

The attune-ai plugin is a Claude Code extension that installs hooks, slash commands, and MCP configuration to give Claude continuous awareness of your workspace — its in-flight specs, git state, context utilization, and safety boundaries.

## Hook responsibilities

The plugin's hooks fire at specific Claude Code lifecycle moments. They fall into five categories.

**Session continuity** — `welcome`, `session_recall`, and `session_stash` orient Claude at session start and preserve state across interruptions. `spec_orient` calls `discover_specs()` to find in-flight specs under your workspace roots, then formats them into an orientation prompt using `format_orientation()` and `render_spec_pin()`.

**Recall** — `jit_recall` consults a curated decision-point → rule map and injects the matching rule at the moment of decision. `lesson_recall` surfaces stored lessons relevant to the current context.

**Compact warning** — `compact_warning` calls `estimate_utilization()` to measure context window consumption and emits a warning via `format_warning()` when utilization crosses a threshold. A session sentinel keyed by `session_sentinel_path()` ensures the warning fires at most once per session; `prune_stale_sentinels()` removes sentinels that outlive their TTL.

**Safety** — `security_guard` validates bash commands against `SEARCH_COMMAND_PREFIXES` and file paths against `SYSTEM_DIRECTORIES` before Claude executes them.

**Help and formatting** — `help_on_error`, `help_post_commit`, and `help_freshness_check` surface relevant help at key moments. `usage_consent_notice` asks once per workspace about anonymous usage sharing when running under MCP / Claude Code. `format_on_save` formats files when Claude writes them.

Every hook that must not run inside an SDK-spawned subprocess calls `exit_if_sdk_subprocess()` at startup. You can inspect the gate condition directly with `is_sdk_subprocess()`.

## Shared state model

Two dataclasses form the shared vocabulary that hooks pass between each other at fire time.

`SpecInfo` represents one in-flight spec discovered under a workspace root. Its core fields are `slug`, `path`, `layer`, `phase`, `status`, and `mtime`. When a status is ambiguous — for example, when the spec header conflicts with an external source — `effective_status` holds the resolved value, `status_source` records where it came from, and `status_conflict` flags the disagreement. `spec_orient` uses two status categories to decide what to surface: terminal statuses (`closed`, `complete`, `completed`, `retired`, `superseded`, `shipped`, `done`) and ongoing statuses (`living`, `ongoing`).

`GitState` is a lightweight worktree snapshot carrying the current `branch`, the `last_sha` and `last_subject` of the most recent commit, and any `uncommitted` file paths. `build_resume_prompt()` in `hooks._resume_prompt` accepts both a `SpecInfo` and a `GitState` to assemble the `/handoff` resume prompt — it is the single source of truth for that format.
