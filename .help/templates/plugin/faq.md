---
type: faq
name: plugin-faq
feature: plugin
depth: faq
generated_at: 2026-05-27T13:42:27.346057+00:00
source_hash: ff7ee791016c71dc1aca7ef059da6fba3d0f06aa842c544cc71910c9900d0b2f
status: generated
---

# Plugin FAQ

## What is the plugin?

The plugin is the Claude Code integration layer: it bundles hooks, slash commands, MCP configuration, and skills that run alongside your Claude Code sessions.

## What hooks does the plugin provide?

The plugin includes hooks for several lifecycle events:

- **`hooks.format_on_save`** — formats files when you save
- **`hooks.help_freshness_check`** — checks whether help content is current
- **`hooks.help_on_error`** — surfaces help when an error occurs
- **`hooks.help_post_commit`** — runs help checks after a commit
- **`hooks.compact_warning`** — warns you when context utilization is high
- **`hooks.security_guard`** — validates bash commands and file paths before execution
- **`hooks.spec_orient`** — orients you to in-flight specs in your workspace
- **`hooks.welcome`** — runs on session start

## What does `security_guard` actually check?

It validates two things: the bash command you're about to run (`validate_bash_command`) and the file path you're about to access (`validate_file_path`). Both return a `(bool, str)` tuple — `True` if the input is allowed, along with a message explaining the decision.

File path validation blocks access to system directories including `/etc`, `/sys`, `/proc`, `/dev`, `/boot`, `/sbin`, `/usr/sbin`, `/private/etc`, and `/private/var`.

## How does the compact warning work?

`estimate_utilization` in `hooks._transcript_size` reads your transcript and returns a float in `[0.0, 1.0]` representing how full your context window is. When that value crosses a threshold, `format_warning` in `hooks.compact_warning` composes a warning that includes a resume prompt so you can continue work in a fresh session.

The resume prompt itself is built by `build_resume_prompt` in `hooks._resume_prompt`, which pulls in the current `SpecInfo` (if any), the `GitState` snapshot, your workspace path, and an optional to-do summary.

## How does the plugin find my in-flight specs?

`discover_specs` in `hooks._state` walks the `specs/` directories under each workspace root and returns a list of `SpecInfo` objects. Each `SpecInfo` carries the spec's `slug`, `path`, `layer`, `phase`, `status`, and `mtime`. Workspace roots are resolved by `workspace_roots`, which defaults to `~/attune` if it can't determine them from your current directory.

## What git information does the plugin use?

`git_state` in `hooks._state` returns a `GitState` snapshot containing your current `branch`, the `last_sha` and `last_subject` of your most recent commit, and a tuple of `uncommitted` file paths. Hooks that build resume prompts and orientation output use this snapshot.

## How do I run the handoff command?

Call `main()` in `hooks._handoff_cli` — it's the entry point for the `/handoff` slash command and returns `0` on success.

## Where are the source files?

All plugin source files live under `plugin/**`.

**Tags:** `plugin`, `claude-code`
