# Plugin CLI reference

Claude Code plugin — skills, hooks, commands, and MCP config.

## Description

The attune-ai plugin bundles the runtime hooks, security guards, and session-continuity helpers that back Claude Code slash commands and MCP tooling. Each hook module exposes a `main()` entry point invoked by Claude Code at specific lifecycle events. Supporting functions handle state discovery, transcript sizing, and prompt rendering.

## Usage

```
plugin [OPTIONS] SUBCOMMAND [ARGS]
```

## Subcommands

### Hook entry points

| Subcommand | Module | Description |
|---|---|---|
| `compact-warning main` | `hooks.compact_warning` | Fires when context utilization crosses a threshold; emits a warning and resume prompt to stderr. Never raises. |
| `format-on-save main` | `hooks.format_on_save` | Reads a PostToolUse payload from stdin and formats Python files in place. |
| `help-freshness-check main` | `hooks.help_freshness_check` | Checks help-template freshness at session start. |
| `help-on-error main` | `hooks.help_on_error` | Reads a PostToolUse payload and suggests relevant help if a tool error is detected. |
| `help-post-commit main` | `hooks.help_post_commit` | Checks for stale help templates after a git commit. |
| `handoff main` | `hooks._handoff_cli` | CLI wrapper for the `/handoff` slash command. Returns `0` on success. |
| `spec-orient main` | `hooks.spec_orient` | Branches on `source`; prints orientation content for in-flight specs. Never raises. |
| `security-guard main` | `hooks.security_guard` | Validates a tool call against security policies. Accepts a context dict; returns a result dict. |
| `welcome main` | `hooks.welcome` | Prints a welcome message to stderr. Claude Code surfaces stderr to the user. |

### State and prompt helpers

| Subcommand | Signature | Description |
|---|---|---|
| `build-resume-prompt` | `spec_info: SpecInfo \| None, git_state: GitState, *, workspace_path='~/attune', todo_summary=None` | Renders the user-facing resume-prompt body as a string. |
| `discover-specs` | `roots: list[Path]` | Walks `specs/` directories under each root and returns a list of `SpecInfo` for in-flight specs. |
| `git-state` | `cwd: Path` | Returns branch name, last commit SHA, last commit subject, and uncommitted files for `cwd`. |
| `session-sentinel-path` | `session_id: str \| None` | Returns the filesystem path for the once-per-session compact-warning sentinel. |
| `prune-stale-sentinels` | `now: float \| None = None` | Deletes sentinel files older than the TTL. Returns the count of deleted files. |
| `workspace-roots` | `cwd: Path \| None = None` | Returns a best-effort list of workspace roots to scan for specs. |
| `estimate-utilization` | `transcript_path: str \| Path` | Returns estimated context utilization as a float in `[0.0, 1.0]`. |
| `format-warning` | `util: float, threshold: float, resume_body: str` | Composes the user-facing warning string and resume prompt. |
| `format-orientation` | `specs: list[SpecInfo]` | Returns a short Markdown list of in-flight specs, used on non-compact session starts. |
| `render-spec-pin` | `spec: SpecInfo, char_budget: int` | Renders a spec body for post-compact context restoration, respecting `char_budget`. |
| `validate-bash-command` | `command: str` | Validates a Bash command against security policies. Returns `(allowed: bool, reason: str)`. |
| `validate-file-path` | `file_path: str` | Validates a file path against security policies. Returns `(allowed: bool, reason: str)`. |

## Options

| Option | Description |
|--------|-------------|
| `--help` | Show help and exit. |

## Data types

### `SpecInfo`

One in-flight spec discovered under a workspace root.

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | Short identifier for the spec. |
| `path` | `Path` | Absolute path to the spec file. |
| `layer` | `str` | Architectural layer the spec belongs to. |
| `phase` | `str` | Current lifecycle phase. |
| `status` | `str` | Current status string. |
| `mtime` | `float` | Last-modified timestamp (Unix epoch). |

### `GitState`

Snapshot of the worktree's git state at hook fire time.

| Field | Type | Description |
|-------|------|-------------|
| `branch` | `str` | Current branch name. |
| `last_sha` | `str` | SHA of the most recent commit. |
| `last_subject` | `str` | Subject line of the most recent commit. |
| `uncommitted` | `tuple[str, ...]` | Paths of uncommitted changes. |

## Output

Hook entry points write to stderr; Claude Code surfaces stderr in the conversation. Example output from `compact-warning main`:

```
⚠️  Context utilization is high. Consider compacting soon.

## Resume from here

Branch: main | a1b2c3d fix: update spec routing
Uncommitted: src/attune/hooks/_state.py

In-flight specs:
- auth-redesign (feature / in-progress)
```

`handoff main` and `spec-orient main` exit with `0` on success and write structured prompt content to stdout for Claude Code to consume.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success. Applies to `handoff main`, `spec-orient main`, and `compact-warning main`. |
| `1` | Unhandled error. Hook entry points documented as "never raises" suppress exceptions internally and may return `0` even when an internal error occurs. |

## Related commands

- `claude plugin install attune-ai@attune-ai` — install the plugin into Claude Code (see `tasks/install-plugin.md`)
- `/attune` — verify the plugin is active inside a Claude Code session
- `/coach` — skill entry point backed by this plugin runtime (see `quickstarts/skill-coach.md`)

<!-- attune-generated: source_hash=ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f feature=plugin kind=cli-reference generated_at=2026-05-27 -->
