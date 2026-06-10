---
type: comparison
name: plugin-comparison
feature: plugin
depth: comparison
generated_at: 2026-06-10T07:07:04.688941+00:00
source_hash: 97a2943dbbe1f0524955dd7678a2b8b4eb09cacaf89d2950ee2705251fcd2249
status: generated
---

# Comparison: Plugin hooks vs direct scripting

## Context

The attune Claude Code plugin ships a suite of lifecycle hooks — session continuity, security validation, spec orientation, transcript monitoring, and formatting. Each hook exposes a `main()` entry point and shares state helpers from `hooks._state`. The question this page answers: **should you wire up the plugin hooks, or solve the problem with a standalone script?**

## Feature comparison

| Capability | Plugin hooks | Standalone script |
|---|---|---|
| **Session continuity** | `session_recall.main()`, `session_stash.main()` handle sentinel creation, pruning, and resume-prompt rendering automatically | You implement sentinel logic from scratch; no TTL pruning |
| **Resume prompt quality** | `build_resume_prompt()` is the single source of truth for prompt format, incorporating `SpecInfo` and `GitState` | You assemble the prompt manually; format drifts from the canonical shape |
| **Spec discovery** | `discover_specs(roots)` walks `specs/` and `docs/specs/` subdirectories and returns typed `SpecInfo` objects | You write your own directory walker with no `effective_status` or `status_conflict` resolution |
| **Git state snapshot** | `git_state(cwd)` returns a `GitState` with `branch`, `last_sha`, `last_subject`, and `uncommitted` files in one call | You shell out to git and parse output yourself |
| **Transcript monitoring** | `estimate_utilization(transcript_path)` returns a `[0.0, 1.0]` float; `format_warning()` composes the user-facing alert | You approximate token load without a calibrated utilization curve |
| **Security validation** | `validate_bash_command()` and `validate_file_path()` check against `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES` | You maintain your own allowlist/blocklist |
| **Spec orientation** | `format_orientation()` and `render_spec_pin()` render context-aware spec summaries with a configurable `char_budget` | You write and maintain your own rendering logic |
| **JIT recall** | `jit_recall.main()` fires per-session recall with sentinel deduplication via `_SENTINEL_PREFIX` | No deduplication; you re-fire on every invocation |
| **Stale sentinel cleanup** | `prune_stale_sentinels(now)` removes expired files automatically | Manual cleanup or accumulating sentinel files |
| **Entry-point contract** | All hooks return `int` (0 on success) or `None`; never raises | Contract is whatever you write |

## Key tradeoffs

**Plugin hooks are more constrained, on purpose.** Each hook does one thing and exposes a narrow surface. If you need to combine `git_state()` with `discover_specs()` in a way the hooks don't anticipate, you call those functions directly from `hooks._state` — the helpers are public.

**Standalone scripts are faster to prototype but slower to maintain.** You avoid the hook wiring overhead, but you re-implement state discovery, sentinel logic, and prompt formatting that the plugin already handles correctly. Once your script grows beyond ~50 lines of state manipulation, you are reimplementing the plugin.

**Security validation is non-trivial to get right.** `validate_bash_command()` and `validate_file_path()` encode specific rules about `SYSTEM_DIRECTORIES` and `SEARCH_COMMAND_PREFIXES`. A standalone script that skips these checks is not equivalent — it is less safe.

## Use plugin hooks when…

- You are hooking into Claude Code lifecycle events (session start/end, post-commit, pre-save, error, compact warning).
- You need reliable resume prompts that stay consistent with `build_resume_prompt()` as the canonical format.
- You want spec-aware orientation (`spec_orient`) or JIT recall without writing your own discovery and deduplication logic.
- Security validation of bash commands or file paths is in scope — use `validate_bash_command()` and `validate_file_path()` rather than rolling your own.
- You need transcript utilization monitoring via `estimate_utilization()`.

## Use a standalone script when…

- You need a one-off automation that touches none of the session, spec, or git state the hooks manage.
- You are prototyping behavior before deciding whether it belongs in a hook at all.
- Your logic genuinely doesn't fit any of the hook entry points and you don't need the shared state infrastructure.

In practice, most persistent Claude Code workflow automation belongs in a hook. Standalone scripts are the right starting point, not the right finishing point.

## Source files

- `plugin/**`

**Tags:** `plugin`, `claude-code`
