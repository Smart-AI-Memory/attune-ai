# attune-help Plugin Spec

**Status:** in-progress (10/11 complete; task 10 manual UI tests pending)
**Created:** 2026-04-07
**Last updated:** 2026-04-09
**Source:** /plan feature
**Route:** feature
**Owner:** Patrick Roebuck
**Depends on:** attune-help library v0.3.0 ([packages/attune-help/](../../../../attune-ai/packages/attune-help/))
**Sibling plans:** [attune-author-plugin.md](../../../../attune-ai/.claude/plans/attune-author-plugin.md) (precedent — same monorepo, same structure)

## Completion Notes (2026-04-08)

Automated work done in session — **167 tests passing across 3 plugins**.

### Tasks 1–9, 11: completed

| Task | Deliverable |
|---|---|
| 1 | Scaffolded `packages/attune-help/plugin/` (core, skills, .claude-plugin) + `src/attune_help/mcp/` + `tests/` |
| 2 | Added `[plugin]` optional extra with `mcp>=0.9.0` + `attune-help-mcp` console script to `pyproject.toml`; refreshed `uv.lock` |
| 3 | Built MCP server: `server.py`, `tool_schemas.py`, `handlers.py`, `path_validation.py` (copied verbatim from attune-author) |
| 4 | Created `.mcp.json` with `uv run --from 'attune-help[plugin]' python -m attune_help.mcp.server` |
| 5 | Created `plugin.json` + plugin-local `marketplace.json` (version 0.3.0) |
| 6 | Hub skill `lookup` (Socratic routing, MCP tools table, collision-safe description) |
| 7 | Work skills: `lookup-topic`, `lookup-warn`, `lookup-list` |
| 8 | Plugin `README.md` with install, skills, MCP tools, ecosystem table |
| 9 | Validation tests: `test_plugin_config.py` (29 tests), `test_plugin_references.py` (11 tests), `test_mcp_server.py` (40 tests) — **80 passing** as of 2026-04-09 |
| 11 | Added attune-help as 3rd entry in root `.claude-plugin/marketplace.json` |

### 6 MCP tools shipped

All use `lookup_*` prefix to avoid collision with attune-ai's `help_*` tools:

- `lookup_topic` — progressive depth lookup (concept → task → reference)
- `lookup_list` — enumerate topics with optional tag filter
- `lookup_warn` — file-context warnings by extension and name
- `lookup_preamble` — one-line "Use X when..." tooltip
- `lookup_reset` — clear session so next lookup starts at concept
- `lookup_status` — read current depth level without advancing (added 2026-04-09)

### Library boundary preserved

`pip install attune-help` (no extra) still works without `mcp` — verified by installing a `MetaPathFinder` that blocks `mcp` imports at runtime, then successfully importing `HelpEngine` and calling `lookup()`. `mcp` is only pulled in by `pip install 'attune-help[plugin]'`.

### One bug caught and fixed during development

`handlers.lookup_topic` initially called `engine.lookup_raw()` *and* `engine.lookup()`, which advanced the session state twice, so the second call returned the next depth level (often `None`). Fix: render from the `PopulatedTemplate` returned by the first call using `engine.render(raw)` — no double-advance. Caught by smoke test before writing formal tests. Locked in with the `test_lookup_topic_does_not_double_advance` regression test (added 2026-04-09, verified to fail when the bug is reintroduced).

### Hardening pass (2026-04-09)

Follow-up session after initial delivery. Four changes landed green in the same run — **80/80 tests passing**.

| Change | What |
|---|---|
| Promote private API | `HelpEngine._render()` → `HelpEngine.render()`. 3 internal callers in `engine.py` updated. Handler no longer reaches into a private method. |
| Regression test | `test_lookup_topic_does_not_double_advance` — asserts session storage is at `depth_level=0` after exactly one handler call. Uses `bug-predict` topic (has con+tas+ref templates) so a double-advance would move state to depth 1. Verified by temporarily reverting the fix: test correctly failed with `depth_level=1, expected 0`. |
| New MCP tool: `lookup_status` | Read-only inspection of session state. Returns `{user_id, last_topic, depth_level, level_label}` without mutating storage. Fills the gap where skills had to remember progression state across calls. |
| Renderer enum validation | `lookup_topic` now defensively checks `renderer` arg against `_VALID_RENDERERS` frozenset before passing to `HelpEngine`. Schema already declared the enum, but not all MCP clients enforce schema enums — bad input now returns a clean `{"success": False, "error": ...}` instead of a cryptic library warning. |
| README troubleshooting | New "Troubleshooting" section in `plugin/README.md` points at `$TMPDIR/attune-help/attune-help-mcp.log` for the case where `/mcp` doesn't show the server. |
| Silent-crash protection | `server.main()` uses `mkdir(parents=True, exist_ok=True)` — if `tempfile.gettempdir()` ever returned a path whose parent doesn't exist, the server would previously crash before logging was set up. |

7 net new tests (80 total, was 73):

- `test_lookup_topic_does_not_double_advance`
- `test_invalid_renderer_rejected` + `test_all_schema_renderers_accepted`
- `TestLookupStatus`: `test_fresh_session_reports_depth_zero`, `test_status_reflects_prior_lookup`, `test_status_is_read_only` (calls status 3× and diffs storage), `test_empty_user_id_rejected`

### Task 10 (manual): PENDING USER

Open a fresh Claude Code session in this repo and work through this checklist:

1. Start with only attune-help loaded:

   ```bash
   claude --plugin-dir packages/attune-help/plugin
   ```

   Expected: server starts without errors; `/mcp` shows the `attune-help` server with **6 tools** (`lookup_topic`, `lookup_list`, `lookup_warn`, `lookup_preamble`, `lookup_reset`, `lookup_status`).

   If `/mcp` doesn't show the server, check the log file at `$TMPDIR/attune-help/attune-help-mcp.log` — nothing is written to stdout so the stdio stream stays clean.

2. Test natural-language triggers (one at a time, in a fresh response):
   - "look up bug-predict" → should route to `lookup-topic` and return the concept view
   - "tell me more" → should advance to the task view (depth 1). Note: only topics with concept+task+reference templates advance cleanly. Known multi-level topics: `bug-predict`, `security-audit`, `smart-test`, `coach`. A topic like `progressive-depth` only has a concept template so "tell me more" will legitimately report no deeper level available.
   - "what topics are available" → should route to `lookup-list`
   - "what should I watch out for in src/app.py" → should route to `lookup-warn`
   - "where am I in the lookup" or "what's my current topic" → should route to `lookup-status` and report the last topic + depth without advancing
   - "reset" or "start over" → should clear session and next lookup returns concept again

3. Install attune-author alongside attune-help and verify no trigger conflict:
   - Ask Claude to author something — should route to `/author` skills
   - Ask Claude to look up something — should route to `/lookup` skills
   - Neither should steal the other's triggers

4. Finally, install all three plugins (attune-ai + attune-author + attune-help):
   - `/coach` (attune-ai) and `/lookup` (attune-help) coexist — verify both work
   - If one steals the other's triggers, narrow the description of the losing skill in a follow-up session. The most likely collision is on "what is" and "explain" — I already scoped `/lookup`'s description to `lookup, look up, depth, topic, help topic, tell me more` to minimize overlap.

When those check out, update Status above from `in-progress` to `completed` and move on.

### What you can already do in a fresh session

```bash
# From the attune-ai repo root:
claude --plugin-dir packages/attune-help/plugin

# Then try any of these natural-language prompts:
"look up bug-predict"          # returns concept view
"tell me more"                 # advances to task view
"where am I"                   # reports current topic + depth (no advance)
"list topics"
"what topics are available tagged python"
"warn me about src/app.py"
"reset"                        # clears session back to concept
```

### Files in scope for this plan

- **New:** [packages/attune-help/plugin/](../../packages/attune-help/plugin/) (full directory)
- **New:** [packages/attune-help/src/attune_help/mcp/](../../packages/attune-help/src/attune_help/mcp/) (4 files)
- **New:** [packages/attune-help/tests/](../../packages/attune-help/tests/) (5 files: `__init__.py`, `conftest.py`, `test_plugin_config.py`, `test_plugin_references.py`, `test_mcp_server.py`)
- **Modified:** [packages/attune-help/pyproject.toml](../../packages/attune-help/pyproject.toml) (added `[plugin]` extra, `[project.scripts]`)
- **Modified:** [packages/attune-help/uv.lock](../../packages/attune-help/uv.lock) (refreshed by `uv lock`)
- **Modified:** [.claude-plugin/marketplace.json](../../.claude-plugin/marketplace.json) (added 3rd plugin entry)
- **Unchanged:** library public API (`HelpEngine`, `LocalFileStorage`, `TemplateContext`, etc.), bundled templates, attune-ai's `/coach` skill, attune-author plugin

## Context

`attune-help` is the runtime that reads `.help/templates/` (created by `attune-author` or written by hand) and serves them with progressive depth, audience adaptation, and renderer choices. Today it ships as a pure Python library on PyPI (v0.3.0), with no skills, no MCP server, and no Claude Code surface. Users who want help reading must install the full `attune-ai` plugin (v5.10.0, 14 skills, large surface) which includes a `/coach` skill.

The attune-author plan completed today added a *writer* plugin without bringing along all of attune-ai. This plan does the same for the *reader* side: a thin Claude Code plugin that pairs with `attune-author` so a user can install `attune-author + attune-help` and get an end-to-end author-and-read workflow without ever needing `attune-ai`.

## Problem

Today, the only way to read `.help/templates/` from inside Claude Code is to install `attune-ai` (the full workflow plugin). For a user who only wants `attune-author` (template authoring) + read-side help lookup, that's a much larger install than they need. They get 14 skills they didn't ask for, plus all of attune-ai's MCP tool surface.

There is no `attune-help` Claude Code plugin. The library is reachable only via `from attune_help import HelpEngine` in Python — no skills, no MCP, no slash commands.

## Goals

- Ship `packages/attune-help/plugin/` as a third installable plugin from the monorepo marketplace
- Users can install `attune-author` + `attune-help` together (no `attune-ai` required) and get a complete author-and-read workflow
- Hub skill `/lookup` does not collide with `attune-ai`'s `/coach` — both can coexist if a user installs all three plugins
- MCP tools use `lookup_*` prefix to avoid collision with attune-ai's `help_lookup`/`help_init`/`help_status`
- `mcp>=0.9.0` is added as an **optional** `[plugin]` extra on attune-help, not a core dep — keeps the library install lean for non-plugin users
- Validation tests mirror attune-author's pattern (config validation, reference validation, MCP server tests)

## End State

- `packages/attune-help/plugin/` exists with: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.mcp.json`, `README.md`, `core/__init__.py`, and 4 skills (`lookup`, `lookup-topic`, `lookup-warn`, `lookup-list`)
- `packages/attune-help/src/attune_help/mcp/` exists with `server.py`, `tool_schemas.py`, `handlers.py`, `path_validation.py` (5 MCP tools: `lookup_topic`, `lookup_list`, `lookup_warn`, `lookup_preamble`, `lookup_reset`)
- `packages/attune-help/tests/` exists (new directory) with `test_mcp_server.py`, `test_plugin_config.py`, `test_plugin_references.py` — all passing
- Root `.claude-plugin/marketplace.json` lists three plugins: `attune-ai`, `attune-author`, `attune-help`
- `pip install 'attune-help[plugin]'` resolves with `mcp>=0.9.0` pulled in; `pip install attune-help` (no extra) still works without it
- `python -m attune_help.mcp.server` starts cleanly and lists 5 tools

## Scope

- **Files to create:** ~25 (plugin scaffolding, MCP server, 4 skills, 3 test files, README)
- **Files to modify:**
  - [packages/attune-help/pyproject.toml](../../../../attune-ai/packages/attune-help/pyproject.toml) — add `[plugin]` optional extra with `mcp>=0.9.0`; add `[project.scripts]` entry for `attune-help-mcp`
  - [.claude-plugin/marketplace.json](../../../../attune-ai/.claude-plugin/marketplace.json) (root) — add third plugin entry
  - [packages/attune-help/uv.lock](../../../../attune-ai/packages/attune-help/uv.lock) — refreshed by `uv lock`
- **Type:** feature (new plugin, mirrors completed `attune-author-plugin.md`)
- **Not changing:**
  - The library's public API (`HelpEngine`, `LocalFileStorage`, `TemplateContext`, etc.) — stays exactly as-is
  - Bundled templates in `src/attune_help/templates/`
  - The existing `attune-ai`'s `/coach` skill or its `help_*` MCP tools
  - The completed `attune-author` plugin

## Critical Constraints

| Constraint | How honored |
|---|---|
| Skill name `/lookup` must not collide with attune-ai's `/coach` or any Claude Code built-in (`/batch`, `/compact`, `/config`, `/cost`, `/help`, `/init`, `/login`, `/logout`, `/memory`, `/permissions`, `/review`, `/status`, `/vim`) | `lookup` is not in the built-in list and is not used by attune-ai or attune-author. Verified. |
| MCP tool names must not duplicate attune-ai's `help_lookup`, `help_init`, `help_status`, `help_update`, `help_maintain` | Use `lookup_*` prefix throughout. |
| Skill descriptions ≤ 250 chars (Anthropic truncates longer ones) | Validated by `test_plugin_config.py` |
| Skill frontmatter allowlist (March 2026): `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context`, `agent`, `hooks`, `paths`, `shell` | Validated by `test_plugin_config.py` |
| `mcp` is heavy — keep core install lean | Make `mcp>=0.9.0` an optional `[plugin]` extra, not a core dep |
| `.mcp.json` must use `uv run --from attune-help`, not bare `python` (lesson: pyenv shim) | Pinned in plugin/.mcp.json |
| Use official `mcp.server.Server` + `stdio_server`, not hand-rolled JSON-RPC loop (lesson) | Required in server.py |
| Path validation reuses the proven helper from attune-author | Copy `path_validation.py` verbatim |
| Version in `pyproject.toml`, `plugin.json`, `marketplace.json` (×2 fields), `core/__init__.py`, root `marketplace.json` must all match | Validated by `test_plugin_config.py::test_all_versions_match` |

## Architecture

```text
packages/attune-help/
├── src/attune_help/          # existing library (unchanged)
│   ├── __init__.py
│   ├── engine.py
│   ├── progression.py
│   ├── storage.py
│   ├── templates.py
│   ├── transformers.py
│   ├── preamble.py
│   ├── templates/            # bundled templates
│   └── mcp/                  # NEW
│       ├── __init__.py
│       ├── server.py         # AttuneHelpMCPServer
│       ├── tool_schemas.py
│       ├── handlers.py
│       └── path_validation.py
├── tests/                    # NEW directory
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_mcp_server.py
│   ├── test_plugin_config.py
│   └── test_plugin_references.py
└── plugin/                   # NEW
    ├── .claude-plugin/
    │   ├── plugin.json
    │   └── marketplace.json
    ├── .mcp.json
    ├── README.md
    ├── core/
    │   └── __init__.py
    └── skills/
        ├── lookup/SKILL.md          # hub skill
        ├── lookup-topic/SKILL.md    # progressive lookup (main UX)
        ├── lookup-warn/SKILL.md     # file-aware warnings
        └── lookup-list/SKILL.md     # enumerate topics
```

## MCP Tools (5 total)

| Tool | Wraps | Purpose |
|---|---|---|
| `lookup_topic` | `engine.lookup()` | Progressive depth lookup. Args: `topic`, optional `depth_override`, optional `audience` |
| `lookup_list` | `_load_cross_links()` + scan | Enumerate available topics. Args: optional `category`, optional `tag`. Returns markdown table |
| `lookup_warn` | `engine.precursor_warnings()` | File-context warnings. Args: `file_path`, optional `max_results`. Returns top N warnings |
| `lookup_preamble` | `engine.preamble()` | One-line "Use X when..." tooltip. Args: `feature_name` |
| `lookup_reset` | manual session ops on `engine._storage` | Clear progression for a topic so the next lookup starts at concept again. Args: optional `topic` (clears all if absent) |

All handlers must:

1. Validate any path argument (`file_path`, `template_dir`) via `path_validation._validate_file_path()`
2. Pin `workspace_root` via `os.getcwd()` at server startup (lesson from MCP work)
3. Return a uniform `{"success": bool, "data": ..., "error": ...}` shape
4. Use specific exception handling, not bare `except`

## Skills Design

### `lookup` (Hub Skill)

Main entry point. Frontmatter:

```yaml
---
name: lookup
description: "Read and explore .help/ documentation. Progressive depth: concept -> task -> reference. Triggers on: lookup, look up, what is, tell me about, explain, depth."
argument-hint: "<topic name or question>"
---
```

Body sections:

- Scoping (`AskUserQuestion` for intent if no argument)
- Routing table (intent -> sub-skill)
- MCP Tools table
- Fallback if MCP not running

### `lookup-topic`

Wraps `lookup_topic` and `lookup_reset`. Asks for the topic if not given, then calls the MCP tool. After printing the result, mentions "say 'tell me more' for next depth level".

### `lookup-warn`

Wraps `lookup_warn`. Asks for a file path (or detects from current selection), calls the tool, prints up to N warnings.

### `lookup-list`

Wraps `lookup_list`. Optionally filters by category (concepts, tasks, references, warnings, etc.) or tag. Renders a markdown table.

## Anthropic Best Practices Checklist

| Rule | Implementation |
|---|---|
| Skill descriptions ≤ 250 chars | Validated by config test |
| Frontmatter allowlist only | Validated by config test |
| Skill dir name == frontmatter name | Validated by config test |
| Description includes trigger keywords | Manual review during drafting |
| `${CLAUDE_PLUGIN_ROOT}` in any hook commands | N/A (no hooks in this plugin) |
| Path validation in MCP handlers | `path_validation._validate_file_path()` |
| No hardcoded API keys in `.mcp.json` | None needed — attune-help doesn't call any AI APIs |
| Version consistency across 6 files | Validated by sync test |
| No name collisions with built-in commands | `/lookup` is safe; verified |
| No name collisions with attune-ai or attune-author skills | `/lookup` is unused; verified |
| MCP tool names don't collide with attune-ai's `help_*` | `lookup_*` prefix throughout |
| Use official `mcp.server.Server` + `stdio_server` | Required in server.py |

## Tasks

<task id="1" name="scaffold-plugin-dirs">
  <objective>
    Create the plugin directory structure under
    packages/attune-help/plugin/ and the empty MCP module
    skeleton under src/attune_help/mcp/.
  </objective>

  <files-to-create>
    <file path="packages/attune-help/plugin/.claude-plugin/.gitkeep">empty</file>
    <file path="packages/attune-help/plugin/skills/.gitkeep">empty</file>
    <file path="packages/attune-help/plugin/core/__init__.py">
      __version__ = "0.3.0"
    </file>
    <file path="packages/attune-help/src/attune_help/mcp/__init__.py">empty module docstring</file>
    <file path="packages/attune-help/tests/__init__.py">empty</file>
  </files-to-create>

  <validation>
    <check>Directory structure matches the architecture diagram</check>
    <check>core/__init__.py version matches pyproject.toml version</check>
  </validation>
</task>

<task id="2" name="optional-mcp-extra">
  <objective>
    Add the [plugin] optional extra to attune-help so installing the
    plugin pulls mcp>=0.9.0 without forcing it on library-only users.
    Add a console script entry point so the MCP server can be invoked
    by name. Refresh the lockfile.
  </objective>

  <context>
    <existing-code path="packages/attune-help/pyproject.toml">
      Current optional-dependencies block has only [rich]. Add [plugin] alongside it.
    </existing-code>
    <existing-code path="packages/attune-author/pyproject.toml">
      Reference for how attune-author wired mcp as a core dep — we are deliberately doing it differently here (extra, not core).
    </existing-code>
  </context>

  <files-to-modify>
    <file path="packages/attune-help/pyproject.toml">
      <change location="[project.optional-dependencies]">
        BEFORE:
          [project.optional-dependencies]
          rich = ["rich>=13.0.0"]

        AFTER:
          [project.optional-dependencies]
          rich = ["rich>=13.0.0"]
          plugin = ["mcp>=0.9.0"]
      </change>
      <change location="[project.scripts] (new section)">
        Add:
          [project.scripts]
          attune-help-mcp = "attune_help.mcp.server:main"
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>`uv lock` succeeds without errors in packages/attune-help/</check>
    <check>`uv pip install -e '.[plugin]'` resolves and brings in mcp</check>
    <check>`uv pip install -e '.'` still works WITHOUT mcp installed (verified by importing attune_help.engine)</check>
  </validation>

  <risks>
    <risk severity="low">
      `uv lock` may pull in transitive deps that conflict with the
      monorepo's other lockfiles. If so, document the conflict and
      pin precise versions.
    </risk>
  </risks>
</task>

<task id="3" name="mcp-server">
  <objective>
    Build the MCP server inside attune_help.mcp using the official
    mcp.server SDK (Server + stdio_server). Wrap HelpEngine with
    5 tool handlers.
  </objective>

  <context>
    <existing-code path="packages/attune-author/src/attune_author/mcp/server.py">
      Reference shape — copy the class structure (workspace_root, _build_dispatch, call_tool, main_loop). The only differences are the tool count (5 not 6) and the handler module imports.
    </existing-code>
    <existing-code path="packages/attune-author/src/attune_author/mcp/path_validation.py">
      Copy this file verbatim into attune_help/mcp/path_validation.py — it's the same security boundary.
    </existing-code>
    <existing-code path="packages/attune-help/src/attune_help/engine.py">
      Library API to wrap. Methods to expose: lookup, precursor_warnings, preamble, get_summary. Plus a custom list/reset.
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-help/src/attune_help/mcp/server.py">
      AttuneHelpMCPServer class. Constructor takes optional workspace_root. Wires 5 tools through a dispatch dict. main() runs stdio_server.
    </file>
    <file path="packages/attune-help/src/attune_help/mcp/tool_schemas.py">
      get_tools() -> dict with 5 entries: lookup_topic, lookup_list, lookup_warn, lookup_preamble, lookup_reset. Each has name, description, inputSchema (JSON Schema).
    </file>
    <file path="packages/attune-help/src/attune_help/mcp/handlers.py">
      AttuneHelpHandlers class. 5 async methods, one per tool. Each instantiates HelpEngine lazily, validates paths via path_validation, returns {"success", "data", "error"} dicts.
    </file>
    <file path="packages/attune-help/src/attune_help/mcp/path_validation.py">
      Copied from attune-author's mcp/path_validation.py. Same _DANGEROUS_PREFIXES, same validate_file_path() function.
    </file>
  </files-to-create>

  <validation>
    <check>`python -m attune_help.mcp.server` starts without raising</check>
    <check>AttuneHelpMCPServer().tools has exactly 5 entries</check>
    <check>Each tool name starts with `lookup_`</check>
    <check>lookup_warn rejects null bytes and system dirs in file_path</check>
    <check>lookup_topic returns a non-None result for a known bundled topic (e.g. "progressive-depth")</check>
    <check>lookup_list with no args returns at least 40 topics (we have 43 concepts bundled)</check>
  </validation>

  <risks>
    <risk severity="medium">
      `engine.precursor_warnings()` requires a `cross_links.json` to be loaded. The bundled templates have one, so the default should work without a user-provided template_dir. Confirm in the smoke test.
    </risk>
  </risks>
</task>

<task id="4" name="mcp-config">
  <objective>
    Create plugin/.mcp.json so Claude Code launches the server
    via uv (avoiding the pyenv shim issue from a past lesson).
  </objective>

  <files-to-create>
    <file path="packages/attune-help/plugin/.mcp.json">
      mcpServers entry that runs `uv run --from 'attune-help[plugin]' python -m attune_help.mcp.server`. No env vars needed (attune-help calls no remote APIs).
    </file>
  </files-to-create>

  <validation>
    <check>JSON parses successfully</check>
    <check>command is `uv`, not `python`</check>
    <check>args use `--from 'attune-help[plugin]'` to ensure the mcp extra is installed</check>
    <check>No hardcoded keys or secrets</check>
  </validation>
</task>

<task id="5" name="plugin-manifest">
  <objective>
    Create plugin.json and marketplace.json with version pinned to
    0.3.0 (matching the library) and metadata describing attune-help.
  </objective>

  <context>
    <existing-code path="packages/attune-author/plugin/.claude-plugin/plugin.json">
      Reference shape
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-help/plugin/.claude-plugin/plugin.json">
      name=attune-help, version=0.3.0, description, author, homepage, repository, license=Apache-2.0, keywords (help, documentation, progressive-depth, lookup, claude-code)
    </file>
    <file path="packages/attune-help/plugin/.claude-plugin/marketplace.json">
      Marketplace entry pointing to ./ with category "developer-tools" and tags (help, documentation, lookup, progressive-depth, runtime)
    </file>
  </files-to-create>

  <validation>
    <check>JSON parses successfully</check>
    <check>All required fields present</check>
    <check>Version is 0.3.0 in plugin.json, marketplace.json metadata, marketplace.json plugins[0]</check>
    <check>Version matches packages/attune-help/pyproject.toml and core/__init__.py</check>
  </validation>
</task>

<task id="6" name="hub-skill">
  <objective>
    Create the lookup hub skill with a Socratic discovery flow.
  </objective>

  <context>
    <existing-code path="packages/attune-author/plugin/skills/author/SKILL.md">
      Pattern reference — has a clean Hub structure with greeting, scoping, execution, routing, MCP tools sections. Mirror it.
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-help/plugin/skills/lookup/SKILL.md">
      Frontmatter: name=lookup, description (≤250 chars) listing triggers (lookup, look up, what is, tell me about, explain, depth, topic), argument-hint
      Body: Greeting line, Scoping (AskUserQuestion if no arg), Execution routing table, Natural Language Routing table, MCP Tools section, MCP Server Not Running fallback
    </file>
  </files-to-create>

  <validation>
    <check>Description is 50-250 chars and includes natural-language triggers</check>
    <check>Frontmatter uses only allowlisted fields (name, description, argument-hint)</check>
    <check>Skill directory name == frontmatter name (lookup)</check>
    <check>Routing table covers all 3 sub-skills</check>
    <check>Description does not duplicate /coach trigger phrases verbatim (avoid weakening attune-ai's coach when both plugins are installed)</check>
  </validation>
</task>

<task id="7" name="work-skills">
  <objective>
    Create the 3 sub-skills (lookup-topic, lookup-warn, lookup-list)
    that wrap individual MCP tools.
  </objective>

  <context>
    <existing-code path="packages/attune-author/plugin/skills/author-status/SKILL.md">
      Reference work-skill structure — scoping, MCP tool call, result formatting, error handling
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-help/plugin/skills/lookup-topic/SKILL.md">
      Progressive lookup. Calls lookup_topic. After result, mentions "say 'tell me more' to escalate depth". Includes lookup_reset for "start over".
    </file>
    <file path="packages/attune-help/plugin/skills/lookup-warn/SKILL.md">
      File-context warnings. Asks for file path (or uses current IDE selection), calls lookup_warn, prints top N warnings.
    </file>
    <file path="packages/attune-help/plugin/skills/lookup-list/SKILL.md">
      Topic enumeration. Optional category/tag filter via AskUserQuestion. Calls lookup_list, renders markdown table.
    </file>
  </files-to-create>

  <validation>
    <check>All 3 SKILL.md files have valid frontmatter (name, description ≤250 chars)</check>
    <check>Every MCP tool referenced exists in tool_schemas.py</check>
    <check>Skill names are unique and match directory names</check>
    <check>Each skill body is &lt; 200 lines</check>
  </validation>
</task>

<task id="8" name="plugin-readme">
  <objective>
    Write a plugin/README.md explaining what attune-help is, how
    to install it from the marketplace, the trigger phrases, and
    the ecosystem positioning vs attune-ai and attune-author.
  </objective>

  <files-to-create>
    <file path="packages/attune-help/plugin/README.md">
      Sections: What it is, Install (marketplace add + install commands), Quick Start (5 trigger examples), Skills (4 with one-liners), MCP Tools (5 with one-liners), When to use this vs attune-ai vs attune-author (ecosystem table)
    </file>
  </files-to-create>

  <validation>
    <check>Includes claude plugin marketplace add + install commands</check>
    <check>Lists all 4 skills with one-line descriptions</check>
    <check>Lists all 5 MCP tools with one-line descriptions</check>
    <check>Shows ecosystem positioning: attune-ai (full) | attune-author (write) | attune-help (read)</check>
    <check>Notes that attune-help can pair with attune-author without needing attune-ai</check>
  </validation>
</task>

<task id="9" name="validation-tests">
  <objective>
    Mirror attune-author's validation test suite for attune-help.
    Three files: config validation, reference validation, MCP server tests.
  </objective>

  <context>
    <existing-code path="packages/attune-author/tests/test_plugin_config.py">
      Reference for JSON/YAML validation, version sync test, frontmatter allowlist check
    </existing-code>
    <existing-code path="packages/attune-author/tests/test_plugin_references.py">
      Reference for cross-tier reference validation (skill -> MCP tool -> handler)
    </existing-code>
    <existing-code path="packages/attune-author/tests/test_mcp_server.py">
      Reference for MCP server boot, tool count, handler shape, path validation tests
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-help/tests/conftest.py">
      Shared fixtures: tmp_workspace, mcp_server, sample_topic. Mirror attune-author's conftest if it has one.
    </file>
    <file path="packages/attune-help/tests/test_plugin_config.py">
      Tests: plugin.json valid, marketplace.json valid, .mcp.json no secrets, SKILL.md frontmatter allowlist, version consistency across 5 files (pyproject.toml, plugin.json, marketplace.json metadata + plugins[0], core/__init__.py)
    </file>
    <file path="packages/attune-help/tests/test_plugin_references.py">
      Tests: every MCP tool name in a skill resolves to tool_schemas.py, every file path reference exists, no orphaned skills, lookup_* prefix enforced
    </file>
    <file path="packages/attune-help/tests/test_mcp_server.py">
      Tests: server starts, lists 5 tools, each handler returns expected shape, path validation rejects bad paths, lookup_topic returns non-None for a bundled topic
    </file>
  </files-to-create>

  <validation>
    <check>All new tests pass</check>
    <check>Tests catch deliberate misspellings (e.g. rename a tool, expect test failure)</check>
    <check>No collision tests pass: assert lookup_* tools, not help_*</check>
    <check>Version sync test catches a deliberate mismatch in plugin.json</check>
  </validation>
</task>

<task id="10" name="local-smoke-test">
  <objective>
    Run automatable smoke checks (MCP server boot, tool listing,
    sample lookup) and document the manual interactive test the
    user must run in a fresh Claude Code session.
  </objective>

  <validation>
    <check>`uv run --from 'attune-help[plugin]' python -m attune_help.mcp.server` starts without errors when piped a no-op stdin</check>
    <check>AttuneHelpMCPServer().tools has exactly 5 entries</check>
    <check>Sample lookup_topic call returns non-None for bundled topic "progressive-depth"</check>
    <check>Sample lookup_list call returns ≥40 topics</check>
    <check>MANUAL: `claude --plugin-dir packages/attune-help/plugin` starts cleanly</check>
    <check>MANUAL: typing "look up progressive depth" triggers lookup-topic</check>
    <check>MANUAL: typing "what topics are available" triggers lookup-list</check>
    <check>MANUAL: MCP tools appear in `/mcp` listing under attune-help server</check>
    <check>MANUAL: install attune-author + attune-help together; verify no conflict</check>
    <check>MANUAL: install all three (attune-ai + author + help); verify /coach and /lookup both work, no skill steals the other's triggers</check>
  </validation>

  <risks>
    <risk severity="medium">
      Installing all three plugins may cause /lookup and /coach to compete for help-related triggers. If observed, narrow lookup's description to focus on "look up", "depth", "topic" and leave "what is", "explain" to /coach. Document the resolution in the parent plan's lessons section.
    </risk>
    <risk severity="low">
      MCP server may fail to handshake if we hand-roll the loop. Use the official mcp.server.Server + stdio_server (lesson learned from earlier MCP work — same lesson applied to attune-author).
    </risk>
  </risks>
</task>

<task id="11" name="marketplace-entry">
  <objective>
    Add attune-help as the third plugin in the repo-root marketplace.json
    so users can install all three plugins from one `marketplace add`.
  </objective>

  <files-to-modify>
    <file path=".claude-plugin/marketplace.json">
      <change location="plugins array">
        Add a third entry pointing to ./packages/attune-help/plugin/ with name "attune-help", version 0.3.0, category "developer-tools", and tags (help, documentation, lookup, progressive-depth, runtime).
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>marketplace.json still parses</check>
    <check>plugins array now has length 3</check>
    <check>names are sorted: ["attune-ai", "attune-author", "attune-help"]</check>
    <check>sources resolve: ./plugin, ./packages/attune-author/plugin, ./packages/attune-help/plugin</check>
    <check>Existing tests still pass (`pytest tests/unit/plugins/test_plugin_config_validation.py`)</check>
  </validation>
</task>

## Verification

Run from the repo root after all tasks:

```bash
cd /Users/patrickroebuck/attune-ai

# 1. Library still installs without the [plugin] extra
cd packages/attune-help
uv pip install -e .
.venv/bin/python -c "from attune_help import HelpEngine; print('library ok:', HelpEngine().lookup('progressive-depth') is not None)"

# 2. Plugin install path works
uv pip install -e '.[plugin]'
.venv/bin/python -c "import mcp; print('mcp installed:', mcp.__name__)"

# 3. MCP server boots and lists 5 tools
.venv/bin/python -c "
from attune_help.mcp.server import AttuneHelpMCPServer
s = AttuneHelpMCPServer()
assert len(s.tools) == 5, f'expected 5 tools, got {len(s.tools)}'
names = sorted(s.tools.keys())
for n in names:
    assert n.startswith('lookup_'), f'tool {n} missing lookup_ prefix'
print('mcp ok:', names)
"

# 4. attune-help plugin tests pass
.venv/bin/python -m pytest tests/test_plugin_config.py tests/test_plugin_references.py tests/test_mcp_server.py -q
cd ../..

# 5. Existing attune-ai plugin tests still pass (no regressions)
.venv/bin/python -m pytest tests/unit/plugins/test_plugin_config_validation.py -q

# 6. attune-author plugin tests still pass (no regressions)
cd packages/attune-author
.venv/bin/python -m pytest tests/test_plugin_config.py tests/test_plugin_references.py tests/test_mcp_server.py -q
cd ../..

# 7. Root marketplace lists all 3 plugins
.venv/bin/python -c "
import json
d = json.load(open('.claude-plugin/marketplace.json'))
names = sorted(p['name'] for p in d['plugins'])
assert names == ['attune-ai', 'attune-author', 'attune-help'], names
print('marketplace ok:', names)
"
```

All seven must pass before considering the plan done. The interactive Claude Code tests in Task 10 are manual and run in a separate session.

## Open Questions

- **Bundle vs detect templates:** The MCP server defaults to `HelpEngine()` which auto-uses bundled templates. If a user has a project-local `.help/templates/`, should the server prefer that? Current proposal: `lookup_topic` accepts an optional `template_dir` argument, defaulting to bundled. If the user runs the plugin in a project with `.help/`, they pass `template_dir=".help/templates"`. Alternative: auto-detect on server startup. Defer to user feedback after first usage.
- **`mcp` extra naming:** Should the optional extra be named `[plugin]` (matches use case) or `[mcp]` (matches dep)? Going with `[plugin]` because users think in terms of "I want the plugin" not "I want mcp". Flag for review.
- **Should attune-author also become `[plugin]`-extra rather than core dep?** This is a follow-up cleanup task — out of scope for this plan but worth noting since it would shrink the attune-author install footprint too.
