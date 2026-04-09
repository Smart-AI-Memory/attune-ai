# attune-author Plugin Spec

**Status:** in-progress (10/12 + 11-auto done; 11-manual pending)
**Created:** 2026-04-07
**Last updated:** 2026-04-07
**Owner:** Patrick Roebuck
**Depends on:** attune-author library v0.1.0
  ([packages/attune-author/](../../packages/attune-author/))

## Vision

Wrap the `attune-author` Python library as a Claude Code
plugin so users can author and maintain documentation through
natural language inside Claude Code, without dropping to a
shell. Provides a focused alternative to the full `attune-ai`
plugin for users who only need help authoring features.

## Audience

- Technical writers who use Claude Code as their editor
- Developers who want a `.help/` system without all of
  attune-ai's workflows
- Plugin authors who need doc-gen for their own plugins
- Anyone publishing to PyPI/marketplaces who wants automated
  doc maintenance

## Distribution

- **Plugin name:** `attune-author`
- **Marketplace:** Installable from
  `Smart-AI-Memory/attune-ai` (same monorepo as attune-ai)
- **Plugin path:** `packages/attune-author/plugin/`
- **Install:**
  ```bash
  claude plugin marketplace add Smart-AI-Memory/attune-ai
  claude plugin install attune-author@attune-ai-plugins
  ```

## Architecture

```
packages/attune-author/
├── src/attune_author/        # existing library (Tasks 1-10 done)
├── tests/                    # existing tests (113 tests, 89% cov)
└── plugin/                   # NEW: Claude Code plugin
    ├── .claude-plugin/
    │   ├── plugin.json
    │   └── marketplace.json
    ├── .mcp.json             # MCP server launch config
    ├── README.md
    ├── core/
    │   └── __init__.py       # version constant
    ├── skills/
    │   ├── author/           # main hub skill
    │   ├── author-init/
    │   ├── author-status/
    │   ├── author-generate/
    │   ├── author-maintain/
    │   └── author-docs/
    ├── agents/
    │   └── doc-writer.md     # 3-stage pipeline subagent
    └── hooks/
        ├── hooks.json
        └── help_post_commit.py
```

## MCP Server

The library has no MCP server today — the existing
`src/attune/mcp/server.py` belongs to attune-ai and exposes
help tools via `attune.help.*`. We need a **new** MCP server
inside the attune-author package that exposes the library as
Claude Code tools.

```
src/attune_author/mcp/
├── __init__.py
├── server.py         # AttuneAuthorMCPServer
├── tool_schemas.py   # JSON schema definitions
└── handlers.py       # async tool handlers
```

### MCP Tools (6 total)

| Tool | Wraps | Purpose |
|------|-------|---------|
| `author_init` | `bootstrap.scan_project` + `manifest.save_manifest` | Discover features and create `.help/features.yaml` |
| `author_status` | `staleness.check_staleness` | Report stale features in markdown |
| `author_generate` | `generator.generate_feature_templates` | Generate templates for one feature |
| `author_maintain` | `maintenance.run_maintenance` | Regenerate all stale features |
| `author_docs` | `doc_gen.generate_docs` | 3-stage doc generation (requires `[ai]`) |
| `author_lookup` | `manifest.resolve_topic` + reads template | Look up help for a topic by name or tag |

All tools must:
1. Validate paths via a local `_validate_file_path()` helper
2. Pin `workspace_root` via `os.getcwd()` at server startup
3. Return a uniform `{"success": bool, "data": ..., "error": ...}` shape

## Skills Design

Following attune-ai's skills-first pattern (no commands
directory). Each skill is a directory under `plugin/skills/`
with one `SKILL.md` file.

### `author` (Hub Skill)

Main entry point. Uses Socratic discovery to route to
sub-skills. Triggers on natural language like "set up help",
"generate docs", "check stale templates".

**Frontmatter:**
```yaml
---
name: author
description: "Documentation authoring hub — generate, maintain, and validate help content. Triggers on: author, write docs, generate documentation, help system, stale templates, doc-gen, README."
argument-hint: "<what you need>"
---
```

**Body sections:**
- Scoping (AskUserQuestion to identify intent)
- Routing table (intent → sub-skill)
- MCP tool reference

### `author-init`

Bootstraps `.help/features.yaml` in a project. Calls
`author_init` MCP tool, presents discovered features for
user confirmation.

### `author-status`

Shows which features are stale. Calls `author_status`,
formats as markdown table.

### `author-generate`

Generates templates for one feature. Asks user which
feature, then calls `author_generate`.

### `author-maintain`

Regenerates all stale features in one pass. Confirms scope
first (all features vs filtered subset), then calls
`author_maintain`.

### `author-docs`

Generates documentation from a source file using the 3-stage
AI pipeline. Asks for target path, doc type, audience, then
calls `author_docs` (or delegates to `doc-writer` agent for
larger jobs).

## Agent: `doc-writer`

A subagent that orchestrates the 3-stage pipeline for
larger doc generation jobs where the inline tool call would
exceed token budgets.

```yaml
---
name: doc-writer
description: "Generate comprehensive documentation through outline -> write -> review pipeline."
tools: Read, Write, Bash
model: sonnet
maxTurns: 15
---
```

Used by `author-docs` skill when target is a directory or
multi-file module.

## Hooks

### `help_post_commit.py` (PostToolUse on Bash)

Detects when `git commit` runs and offers to refresh stale
templates for files touched by the commit. Based on
`maintenance.run_hook()`.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python ${CLAUDE_PLUGIN_ROOT}/hooks/help_post_commit.py",
            "timeout": 10000
          }
        ]
      }
    ]
  }
}
```

The hook is **non-blocking** (always exits 0). It surfaces a
suggestion via stderr when stale features are detected, but
never blocks the commit.

## Anthropic Best Practices Checklist

| Rule | Implementation |
|------|----------------|
| Skill descriptions ≤ 250 chars | Validated by config test |
| Frontmatter allowlist only | Validated by config test |
| Skill dir name == frontmatter name | Validated by config test |
| Description includes trigger keywords | Manual review during drafting |
| `${CLAUDE_PLUGIN_ROOT}` in all hook commands | Validated by config test |
| Path validation in MCP handlers | Implemented in `_validate_file_path()` |
| No hardcoded API keys in `.mcp.json` | Use `${ANTHROPIC_API_KEY}` substitution |
| Hook timeouts 1-60 seconds | Validated by config test |
| Version match across plugin.json, marketplace.json, core/__init__.py, library `__version__` | Validated by sync test |
| No name collisions with built-in commands | `/author` is safe; verified |
| Avoid `/init` collision | Use `author-init` skill, not `/init` command |
| Reference validation (skill→tool, etc.) | Validated by reference test |

## Tasks

<task id="1" name="scaffold-plugin-dirs">
  <objective>
    Create the plugin directory structure under
    packages/attune-author/plugin/ with empty placeholders
    for all the files we'll write.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/plugin/.claude-plugin/.gitkeep">empty</file>
    <file path="packages/attune-author/plugin/skills/.gitkeep">empty</file>
    <file path="packages/attune-author/plugin/agents/.gitkeep">empty</file>
    <file path="packages/attune-author/plugin/hooks/.gitkeep">empty</file>
    <file path="packages/attune-author/plugin/core/__init__.py">
      Version constant: __version__ = "0.1.0"
    </file>
  </files-to-create>

  <validation>
    <check>Directory structure matches the architecture diagram</check>
  </validation>
</task>

<task id="2" name="plugin-manifest">
  <objective>
    Create plugin.json and marketplace.json with all required
    fields and the version pinned to 0.1.0 to match the
    library.
  </objective>

  <context>
    <existing-code path="plugin/.claude-plugin/plugin.json">
      Reference shape from attune-ai plugin
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/plugin/.claude-plugin/plugin.json">
      name, version, description, author, homepage, repository, license, keywords
    </file>
    <file path="packages/attune-author/plugin/.claude-plugin/marketplace.json">
      Marketplace entry pointing to ./ with category "developer-tools"
    </file>
  </files-to-create>

  <validation>
    <check>JSON parses successfully</check>
    <check>All required fields present</check>
    <check>Version is 0.1.0 in all three files (plugin.json, marketplace.json metadata, marketplace.json plugins[0])</check>
  </validation>
</task>

<task id="3" name="mcp-server">
  <objective>
    Build a standalone MCP server inside the attune_author
    package that exposes the library API as 6 MCP tools.
    Server uses the official mcp.server SDK.
  </objective>

  <context>
    <existing-code path="src/attune/mcp/server.py">
      Reference for stdio server setup, tool dispatch, path validation
    </existing-code>
    <existing-code path="src/attune_author/manifest.py">
      Library API to wrap
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/src/attune_author/mcp/__init__.py">
      Module docstring
    </file>
    <file path="packages/attune-author/src/attune_author/mcp/server.py">
      AttuneAuthorMCPServer class with main_loop using
      mcp.server.Server + mcp.server.stdio.stdio_server
    </file>
    <file path="packages/attune-author/src/attune_author/mcp/tool_schemas.py">
      JSON schemas for the 6 tools
    </file>
    <file path="packages/attune-author/src/attune_author/mcp/handlers.py">
      Async handlers, one per tool
    </file>
    <file path="packages/attune-author/src/attune_author/mcp/path_validation.py">
      Local _validate_file_path() helper (no traversal, no system dirs, no null bytes, optional workspace root)
    </file>
  </files-to-create>

  <files-to-modify>
    <file path="packages/attune-author/pyproject.toml">
      <change location="dependencies">
        Add mcp>=0.9.0 to core dependencies
      </change>
      <change location="[project.scripts]">
        Add: attune-author-mcp = "attune_author.mcp.server:main"
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>Server starts via `python -m attune_author.mcp.server`</check>
    <check>All 6 tools listed via tools/list MCP request</check>
    <check>author_status returns markdown for the test fixture project</check>
    <check>Path validation rejects null bytes, system dirs, traversal</check>
  </validation>

  <risks>
    <risk severity="medium">
      Adding `mcp` to core deps increases install size for
      library-only users. Consider making it an optional
      `[plugin]` extra and shipping the MCP server only when
      that extra is installed.
    </risk>
  </risks>
</task>

<task id="4" name="mcp-config">
  <objective>
    Create .mcp.json so Claude Code knows how to launch the
    MCP server when the plugin loads.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/plugin/.mcp.json">
      mcpServers entry that runs `uv run --from attune-author python -m attune_author.mcp.server` with ANTHROPIC_API_KEY env var
    </file>
  </files-to-create>

  <validation>
    <check>JSON parses successfully</check>
    <check>No hardcoded API keys (use ${ANTHROPIC_API_KEY})</check>
    <check>Command uses `uv run --from` to ensure correct package resolution (lesson learned from .mcp.json pyenv shim issue)</check>
  </validation>
</task>

<task id="5" name="hub-skill">
  <objective>
    Create the main `author` hub skill that uses Socratic
    discovery to route to sub-skills.
  </objective>

  <context>
    <existing-code path="plugin/skills/attune-hub/SKILL.md">
      Reference pattern for hub skill — scoping, routing table, MCP tools section
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/plugin/skills/author/SKILL.md">
      Frontmatter: name=author, description with triggers (≤250 chars), argument-hint
      Body: Scoping section, Routing table, MCP Tools table, fallback if MCP not running
    </file>
  </files-to-create>

  <validation>
    <check>Description is 50-250 chars and includes natural-language triggers</check>
    <check>Frontmatter uses only allowlisted fields</check>
    <check>Skill directory name matches frontmatter name</check>
    <check>Routing table covers all 5 sub-skills</check>
  </validation>
</task>

<task id="6" name="work-skills">
  <objective>
    Create the 5 sub-skills (init, status, generate, maintain,
    docs) that wrap individual MCP tools.
  </objective>

  <context>
    <existing-code path="plugin/skills/doc-gen/SKILL.md">
      Reference pattern for work skills — scoping, MCP tools, execution, output format
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/plugin/skills/author-init/SKILL.md">
      Bootstraps .help/features.yaml; uses author_init tool
    </file>
    <file path="packages/attune-author/plugin/skills/author-status/SKILL.md">
      Reports staleness; uses author_status tool
    </file>
    <file path="packages/attune-author/plugin/skills/author-generate/SKILL.md">
      Generates templates for one feature; uses author_generate tool
    </file>
    <file path="packages/attune-author/plugin/skills/author-maintain/SKILL.md">
      Regenerates all stale features; uses author_maintain tool
    </file>
    <file path="packages/attune-author/plugin/skills/author-docs/SKILL.md">
      AI doc generation from source; uses author_docs tool or doc-writer agent
    </file>
  </files-to-create>

  <validation>
    <check>All 5 SKILL.md files have valid frontmatter (name, description ≤250 chars)</check>
    <check>Every MCP tool referenced exists in tool_schemas.py</check>
    <check>Skill names are unique and match directory names</check>
    <check>Each skill body is &lt; 200 lines</check>
  </validation>
</task>

<task id="7" name="doc-writer-agent">
  <objective>
    Create the doc-writer subagent that runs the 3-stage
    pipeline for larger jobs.
  </objective>

  <context>
    <existing-code path="plugin/agents/setup-guide.md">
      Reference pattern for agent frontmatter and body
    </existing-code>
    <existing-code path="src/attune_author/doc_gen/pipeline.py">
      Pipeline being wrapped
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/plugin/agents/doc-writer.md">
      Frontmatter: name=doc-writer, tools=Read,Write,Bash, model=sonnet, maxTurns=15
      Body: Purpose, Steps (outline → write → review), Output format, Error handling
    </file>
  </files-to-create>

  <validation>
    <check>Agent frontmatter is valid YAML</check>
    <check>name matches file prefix</check>
    <check>Tools list only includes Claude Code built-ins</check>
  </validation>
</task>

<task id="8" name="post-commit-hook">
  <objective>
    Create a non-blocking PostToolUse hook that detects git
    commits and surfaces stale-template suggestions via
    stderr.
  </objective>

  <context>
    <existing-code path="src/attune_author/maintenance.py">
      run_hook() function — already filters by changed files
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/plugin/hooks/hooks.json">
      PostToolUse hook on Bash matcher, points to help_post_commit.py
    </file>
    <file path="packages/attune-author/plugin/hooks/help_post_commit.py">
      Reads tool_input from stdin, detects `git commit` in command, calls run_hook(), prints suggestions to stderr, always exits 0
    </file>
  </files-to-create>

  <validation>
    <check>Hook script is executable and runs without error</check>
    <check>Hook command uses ${CLAUDE_PLUGIN_ROOT}</check>
    <check>Hook timeout is 1000-60000 ms</check>
    <check>Hook exits 0 even when run_hook() raises (non-blocking)</check>
    <check>Suggestions go to stderr, not stdout</check>
  </validation>

  <risks>
    <risk severity="low">
      The hook fires on every Bash call, not just git commits.
      Filter inside the script by checking if `git commit` is
      in tool_input.command.
    </risk>
  </risks>
</task>

<task id="9" name="plugin-readme">
  <objective>
    Write a README.md for the plugin explaining what it does,
    how to install it from the marketplace, and the natural
    language triggers users can say.
  </objective>

  <files-to-create>
    <file path="packages/attune-author/plugin/README.md">
      Sections: What it is, Install, Quick Start (5 trigger examples), Skills, MCP Tools, Hooks, Ecosystem positioning vs attune-ai
    </file>
  </files-to-create>

  <validation>
    <check>Includes claude plugin marketplace add + install commands</check>
    <check>Lists all 6 skills with one-line descriptions</check>
    <check>Shows ecosystem diagram (attune-help → attune-author → attune-ai)</check>
  </validation>
</task>

<task id="10" name="validation-tests">
  <objective>
    Mirror the attune-ai plugin validation tests for
    attune-author's plugin. These run as part of the existing
    pytest suite and gate releases.
  </objective>

  <context>
    <existing-code path="tests/unit/plugins/test_plugin_config_validation.py">
      Reference for JSON/YAML validation patterns
    </existing-code>
    <existing-code path="tests/unit/plugins/test_plugin_reference_validation.py">
      Reference for cross-tier reference validation
    </existing-code>
  </context>

  <files-to-create>
    <file path="packages/attune-author/tests/test_plugin_config.py">
      Tests: plugin.json valid, marketplace.json valid, .mcp.json no secrets, hooks.json valid, SKILL.md frontmatter (per skill), version consistency across 4 files (plugin.json, marketplace.json metadata + plugins[0], core/__init__.py, library __version__)
    </file>
    <file path="packages/attune-author/tests/test_plugin_references.py">
      Tests: every MCP tool name in a skill resolves to tool_schemas.py, every file path reference exists, no orphaned skills
    </file>
    <file path="packages/attune-author/tests/test_mcp_server.py">
      Tests: server starts, lists 6 tools, each handler returns expected shape, path validation rejects bad paths
    </file>
  </files-to-create>

  <validation>
    <check>All new tests pass</check>
    <check>Tests catch deliberate misspellings (e.g. rename a tool, expect test failure)</check>
    <check>Coverage on mcp/ stays above 85%</check>
  </validation>
</task>

<task id="11" name="local-smoke-test">
  <objective>
    Run the plugin locally in Claude Code with
    `claude --plugin-dir` and verify all skills, the MCP
    server, and the hook actually work end-to-end.
  </objective>

  <validation>
    <check>`claude --plugin-dir packages/attune-author/plugin` starts without errors</check>
    <check>Typing "set up help in this project" triggers author-init</check>
    <check>Typing "what's stale?" triggers author-status</check>
    <check>MCP tools appear in `/mcp` listing</check>
    <check>Running git commit shows help suggestion via hook</check>
  </validation>

  <risks>
    <risk severity="medium">
      MCP server may not handshake correctly if we hand-roll
      the loop. Use the official mcp.server.Server +
      stdio_server (lesson learned from earlier MCP work).
    </risk>
  </risks>
</task>

## Completion Notes (2026-04-07)

Resumed via `feature-resume-attune-author-plugin-2026-04-07.md`.

- **Tasks 1–10:** completed in original session
- **Task 11 (automated parts):** completed
  - MCP server boots and exposes 6 tools (`author_docs`,
    `author_generate`, `author_init`, `author_lookup`,
    `author_maintain`, `author_status`)
  - `help_post_commit.py` exits 0 cleanly in all 3 payload
    shapes (non-Bash, Bash non-commit, Bash + git commit)
- **Task 11 (manual interactive test):** **PENDING USER**
  - Run `claude --plugin-dir packages/attune-author/plugin`
  - Verify natural-language triggers route to skills
    ("set up help in this project" → author-init,
    "what's stale?" → author-status)
  - Confirm `/mcp` shows the 6 tools
  - Confirm running `git commit` surfaces hook output
- **Task 12:** completed
  - Root `.claude-plugin/marketplace.json` now lists both
    `attune-ai` (./plugin) and `attune-author`
    (./packages/attune-author/plugin)
  - Both validation pipelines green:
    `tests/unit/plugins/test_plugin_config_validation.py`
    (29 passed) and the attune-author plugin suite
    (66 passed)

<task id="12" name="marketplace-entry">
  <objective>
    Add attune-author to the repo-root marketplace.json so
    users can install it from GitHub via the same source as
    attune-ai.
  </objective>

  <files-to-modify>
    <file path=".claude-plugin/marketplace.json">
      <change location="plugins array">
        Add a second entry pointing to ./packages/attune-author/plugin/ with name "attune-author"
      </change>
    </file>
  </files-to-modify>

  <validation>
    <check>marketplace.json still parses</check>
    <check>Both attune-ai and attune-author entries appear</check>
    <check>`claude plugin marketplace list` shows both plugins</check>
  </validation>
</task>
