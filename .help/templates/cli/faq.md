---
type: faq
name: cli-faq
feature: cli
depth: faq
generated_at: 2026-07-14T15:58:48.480621+00:00
source_hash: bd2a2253f6a68a6b8671e90b653a8b827a19319e732c7538d504fb7c9e90bdb4
status: generated
---

# Cli FAQ

## How do I run the CLI?

`attune <command>` (the installed console script) or `python -m
attune.cli_minimal`. Start with `attune --help` / `attune doctor`.

## How do I run a workflow from the terminal?

`attune workflow run <slug>` (e.g. `attune workflow run
code-review`); `attune workflow list` shows the options.

## Is the router synchronous?

`is_slash_command` and `SmartRouter.list_workflows` are sync;
`route_user_input` and `SmartRouter.route` are async (use `route_sync`
for a sync call).

## What's the difference between the CLI and the MCP server?

Same capabilities, different surface — the CLI is for the
terminal/scripting; the MCP server exposes them as tools inside Claude
Code.
