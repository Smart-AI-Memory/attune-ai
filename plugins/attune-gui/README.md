# attune-gui Plugin

A Claude Code plugin that launches the
[attune-gui](https://github.com/Smart-AI-Memory/attune-gui) dashboard in
the Cowork preview pane with a single command — or hands-free when you
ask the model to "open the dashboard".

## What you get

The dashboard's Cowork sidebar (server-rendered Jinja2, ships with the PyPI
package — no `npm` step):

- **Health** — cross-layer version + import probe of `attune-rag`,
  `attune-help`, `attune-author`, `attune-gui`, plus a corpus snapshot
- **Templates** — markdown templates with mtime staleness, tags,
  AI-generated vs. manually-pinned filter, and a per-row pin toggle
- **Specs** — feature specs in `specs/<feature>/` with phase + status
  badges and direct links to each phase file
- **Summaries** — inline-editable `summaries.json` with regen-overwrite warning
- **Living Docs** — workspace editor, scan trigger, document health,
  review queue, and RAG quality bars
- **Commands** — run any registered attune command from a card grid
- **Jobs** — history with per-feature progress, last-output column,
  Cancel button, and auto-refresh

## Requirements

- Claude Code with Cowork (preview pane support)
- [uv](https://docs.astral.sh/uv/) on your `PATH`
- `attune-gui >= 0.5.0` installed (`pip install attune-gui`) **or** the
  repo cloned locally

## Install

This plugin lives in the
[attune-ai](https://github.com/Smart-AI-Memory/attune-ai) marketplace
alongside `attune-ai`, `attune-help`, and `attune-author`. From inside
Claude Code:

```
/plugin marketplace add Smart-AI-Memory/attune-ai
/plugin install attune-gui@attune-ai
```

## Usage

Two ways to launch:

**Slash command** — explicit:

```
/attune-gui
```

**Natural language** — the skill's trigger description picks up phrases like:

```
open the dashboard
show me living docs
launch the attune-gui dashboard
```

Either path runs the same logic:

1. Detects your attune-gui project path (current directory or `./attune-gui/`)
2. Writes `.claude/launch.json` with the correct `uv run` configuration (idempotent)
3. Calls `mcp__Claude_Preview__preview_start` — Cowork starts the sidecar and
   opens the dashboard in the preview pane

## Optional environment

For `Commands` page actions that need an Anthropic key (e.g. `author.regen`,
`author.maintain`), the sidecar auto-loads `.env` from `./`, the
attune-gui repo root, `~/.attune-gui/`, or `~/.attune/`. Common keys:

```
ANTHROPIC_API_KEY=sk-ant-…
ATTUNE_SPECS_ROOT=/path/to/your/repo/specs
ATTUNE_WORKSPACE=/path/to/your/project
```

## License

Apache-2.0
