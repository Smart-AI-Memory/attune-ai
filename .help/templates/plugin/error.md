---
type: error
name: plugin-error
feature: plugin
depth: error
generated_at: 2026-05-27T13:42:27.336356+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Plugin errors

## Common error signatures

Failures in the plugin's hooks fall into three categories:

- **State discovery failures** — `discover_specs()` raises when it cannot walk a `specs/` directory under a workspace root (for example, a `PermissionError` or a root that no longer exists). `workspace_roots()` returning an empty list silently produces an empty spec scan, which causes `format_orientation()` in `hooks.spec_orient` to render nothing.
- **Git state failures** — `git_state()` raises when `cwd` is not inside a git repository or the `git` binary is not on `PATH`. The resulting `GitState` fields (`branch`, `last_sha`, `last_subject`, `uncommitted`) are never populated, so any downstream call to `build_resume_prompt()` that depends on them will receive incomplete data.
- **Security guard rejections** — `validate_bash_command()` and `validate_file_path()` in `hooks.security_guard` return `(False, <reason>)` when a command matches a blocked prefix or a path falls under a `SYSTEM_DIRECTORIES` entry such as `/etc`, `/sys`, or `/proc`. These are not exceptions — they are structured rejections that `main()` in `hooks.security_guard` converts into a blocked response.
- **Utilization estimation failures** — `estimate_utilization()` in `hooks._transcript_size` raises when the transcript path does not exist or is unreadable. When this happens, `format_warning()` in `hooks.compact_warning` never receives a valid `util` float, so no compact warning is emitted.
- **Sentinel path errors** — `session_sentinel_path()` raises if the session ID resolves to an unwritable location. `prune_stale_sentinels()` silently returns `0` if no sentinels are found, which is expected, but an `OSError` here indicates a filesystem permission problem.

## Where errors originate

| Function | Module | What goes wrong |
|---|---|---|
| `main()` | `hooks._handoff_cli` | Entry point for `/handoff`; any unhandled exception from the call chain surfaces here as a non-zero exit |
| `build_resume_prompt()` | `hooks._resume_prompt` | Receives `None` for `spec_info` when discovery found nothing; downstream templates render without spec context |
| `discover_specs()` | `hooks._state` | Raises on unreadable `specs/` directories; returns an empty list when roots are empty |
| `git_state()` | `hooks._state` | Raises when `cwd` is not a git repo or `git` is unavailable |
| `session_sentinel_path()` | `hooks._state` | Raises when the resolved path is unwritable |
| `estimate_utilization()` | `hooks._transcript_size` | Raises on a missing or unreadable transcript file |
| `validate_bash_command()` / `validate_file_path()` | `hooks.security_guard` | Returns `(False, reason)` — not an exception, but the `main()` caller must check the boolean |

## How to diagnose

1. **Identify the hook entry point that failed.** Each hook module exposes a `main()` function. The hook name in the error output (`handoff`, `compact_warning`, `spec_orient`, `security_guard`, and so on) tells you which `main()` was active when the failure occurred.

2. **Check whether `discover_specs()` returned an empty list.** If `workspace_roots()` found no roots, `discover_specs()` receives an empty `roots` list and returns `[]`. This produces no exception — the symptom is a silent no-op in `format_orientation()` or a `build_resume_prompt()` call where `spec_info` is `None`.

3. **Verify git availability for `git_state()` failures.** Run `git rev-parse --show-toplevel` in the working directory. If that fails, `git_state()` will fail for the same reason, and `GitState.branch`, `GitState.last_sha`, and `GitState.last_subject` will be unpopulated.

4. **For security guard rejections, check the return value, not the exception.** `validate_bash_command()` and `validate_file_path()` signal rejection via `(False, reason_string)` — they do not raise. If a command or path is being silently blocked, print the second element of the return tuple to read the rejection reason. Blocked path prefixes include everything under `SYSTEM_DIRECTORIES`: `/etc`, `/sys`, `/proc`, `/dev`, `/boot`, `/sbin`, `/usr/sbin`, `/private/etc`, and `/private/var`.

5. **For utilization warnings that never appear,** confirm that the transcript file passed to `estimate_utilization()` exists and is readable. A missing transcript causes an exception that prevents `format_warning()` from composing the warning and resume prompt.

## Source files

- `hooks._handoff_cli`
- `hooks._resume_prompt`
- `hooks._state`
- `hooks._transcript_size`
- `hooks.compact_warning`
- `hooks.format_on_save`
- `hooks.help_freshness_check`
- `hooks.help_on_error`
- `hooks.help_post_commit`
- `hooks.security_guard`
- `hooks.spec_orient`
- `hooks.welcome`

**Tags:** `plugin`, `claude-code`
