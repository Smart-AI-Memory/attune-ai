# Resume: attune-author Plugin Plan

**Created:** 2026-04-07
**Source:** /plan (resume)
**Route:** feature
**Status:** pending
**Parent plan:** [.claude/plans/attune-author-plugin.md](../../../../attune-ai/.claude/plans/attune-author-plugin.md)

## Context

The `attune-author-plugin.md` plan (12 tasks) is 10/12 complete. All plugin scaffolding, MCP server, 6 skills, hub skill, doc-writer agent, post-commit hook, README, and validation tests are in place. 66 plugin tests pass (`test_plugin_config.py`, `test_plugin_references.py`, `test_mcp_server.py`).

Two tasks remain:

- **Task 11** — local smoke test (MCP server boots, hook runs, plugin loads)
- **Task 12** — add `attune-author` entry to the root `.claude-plugin/marketplace.json` so users can install it from the monorepo marketplace alongside `attune-ai`

## Problem

Without these two tasks, the plugin is untested end-to-end and unreachable from the marketplace. Users cannot run `claude plugin install attune-author@attune-ai` because the root marketplace file only lists `attune-ai`.

## Goals

- Add `attune-author` as a second entry in `.claude-plugin/marketplace.json` (root) so both plugins are installable from one `marketplace add` command
- Verify automated portions of task 11: MCP server starts and lists 6 tools; post-commit hook exits 0 cleanly in both trigger and no-op paths
- Flag the manual-only portion (natural-language skill triggers inside an interactive Claude session) so the user knows what still needs human eyes

## End State

- Root `.claude-plugin/marketplace.json` has two plugin entries (`attune-ai`, `attune-author`)
- `python -m attune_author.mcp.server` prints the initialization log line and responds to a `tools/list` MCP request with 6 tools
- `help_post_commit.py` exits 0 when fed a `git commit` Bash payload (both with and without `.help/features.yaml` present)
- Parent plan `attune-author-plugin.md` Status updated to `in-progress` (or `completed` if user also completes the manual test)
- `test_plugin_config_validation.py`-style tests still pass after the root marketplace edit

## Scope

- **Files to modify:**
  - [.claude-plugin/marketplace.json](/Users/patrickroebuck/attune-ai/.claude-plugin/marketplace.json) — add second plugin entry
  - [.claude/plans/attune-author-plugin.md](/Users/patrickroebuck/attune-ai/.claude/plans/attune-author-plugin.md) — mark tasks 11/12 status
- **Files to read (no edit):**
  - [packages/attune-author/plugin/.claude-plugin/marketplace.json](/Users/patrickroebuck/attune-ai/packages/attune-author/plugin/.claude-plugin/marketplace.json) — source of truth for the attune-author plugin entry shape
  - [packages/attune-author/src/attune_author/mcp/server.py](/Users/patrickroebuck/attune-ai/packages/attune-author/src/attune_author/mcp/server.py) — verify startup path
  - [packages/attune-author/plugin/hooks/help_post_commit.py](/Users/patrickroebuck/attune-ai/packages/attune-author/plugin/hooks/help_post_commit.py) — verify hook shape
- **Type:** feature (plan resume)
- **Not changing:** any plugin skills, MCP handlers, library code, or the standalone `packages/attune-author/plugin/.claude-plugin/marketplace.json` (that file stays for when attune-author is eventually extracted to its own repo)

## Approach

### Step 1 — Task 12: extend root marketplace.json

Read [packages/attune-author/plugin/.claude-plugin/marketplace.json](/Users/patrickroebuck/attune-ai/packages/attune-author/plugin/.claude-plugin/marketplace.json) for the canonical `attune-author` plugin entry. Copy the plugin object (name, description, author, homepage, repository, license, category, tags, version) into the `plugins` array of [.claude-plugin/marketplace.json](/Users/patrickroebuck/attune-ai/.claude-plugin/marketplace.json). Override `source` to `"./packages/attune-author/plugin"` (the path relative to the root marketplace file). Keep the root marketplace `metadata` unchanged — that describes the monorepo marketplace as a whole, not any single plugin.

End state for the root `plugins` array:

```json
[
  { "name": "attune-ai",      "source": "./plugin",                          "version": "5.10.0", ... },
  { "name": "attune-author",  "source": "./packages/attune-author/plugin",   "version": "0.1.0",  ... }
]
```

Then validate with:

```bash
.venv/bin/python -c "import json; d = json.load(open('.claude-plugin/marketplace.json')); \
  assert len(d['plugins']) == 2; \
  names = sorted(p['name'] for p in d['plugins']); \
  assert names == ['attune-ai', 'attune-author'], names; \
  print('marketplace ok:', names)"
```

### Step 2 — Task 11 (automatable parts): MCP server smoke test

Confirm the MCP server initializes and lists 6 tools without starting a live stdio loop:

```bash
cd /Users/patrickroebuck/attune-ai/packages/attune-author
.venv/bin/python -c "
from attune_author.mcp.server import AttuneAuthorMCPServer
s = AttuneAuthorMCPServer()
assert len(s.tools) == 6, f'expected 6 tools, got {len(s.tools)}'
print('tools:', sorted(s.tools.keys()))
"
```

Expected output names: `author_init`, `author_status`, `author_generate`, `author_maintain`, `author_docs`, `author_lookup`.

### Step 3 — Task 11 (automatable parts): post-commit hook smoke test

Exercise the hook in both the trigger and no-op paths using piped JSON payloads:

```bash
# No-op: non-Bash tool → exit 0, no stderr
echo '{"tool_name":"Read","tool_input":{}}' | \
  .venv/bin/python packages/attune-author/plugin/hooks/help_post_commit.py; echo "exit=$?"

# No-op: Bash but not git commit → exit 0, no stderr
echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' | \
  .venv/bin/python packages/attune-author/plugin/hooks/help_post_commit.py; echo "exit=$?"

# Trigger path: Bash + git commit, no .help/ present → exit 0, no stderr
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | \
  .venv/bin/python packages/attune-author/plugin/hooks/help_post_commit.py; echo "exit=$?"
```

All three must print `exit=0`. The first two should print nothing; the third should also print nothing because the repo root has no `.help/features.yaml`.

### Step 4 — Task 11 (manual part): flag the interactive test

The plan's remaining checks — "typing 'set up help in this project' triggers author-init", "MCP tools appear in `/mcp` listing", "running git commit shows help suggestion via hook" — require a fresh Claude Code session started with `claude --plugin-dir packages/attune-author/plugin`. That cannot be run from inside the current Claude session. Document this in the parent plan as a manual checklist for the user to work through, and leave the parent plan Status at `in-progress` until the user reports back.

### Step 5 — Update parent plan status

Edit [.claude/plans/attune-author-plugin.md](/Users/patrickroebuck/attune-ai/.claude/plans/attune-author-plugin.md): change Status from `Draft` to `in-progress`. Add a short "Completion notes" section at the bottom listing:

- Tasks 1–10, 12: completed
- Task 11: automated checks passed (MCP server + hook), manual interactive test pending user verification

## Verification

Run in order from the repo root:

```bash
cd /Users/patrickroebuck/attune-ai

# 1. marketplace JSON is valid and has both plugins
.venv/bin/python -c "import json; d = json.load(open('.claude-plugin/marketplace.json')); \
  assert sorted(p['name'] for p in d['plugins']) == ['attune-ai', 'attune-author']; print('ok')"

# 2. existing plugin config tests still pass (does not validate the root marketplace, but proves we didn't break the attune-ai plugin marketplace file)
.venv/bin/python -m pytest tests/unit/plugins/test_plugin_config_validation.py -q

# 3. attune-author plugin tests still pass
cd packages/attune-author && .venv/bin/python -m pytest tests/test_plugin_config.py tests/test_plugin_references.py tests/test_mcp_server.py -q && cd ../..

# 4. MCP server boots
cd packages/attune-author && .venv/bin/python -c "
from attune_author.mcp.server import AttuneAuthorMCPServer
s = AttuneAuthorMCPServer(); assert len(s.tools) == 6; print('mcp ok')
" && cd ../..

# 5. Hook script runs clean in all three payload shapes (see Step 3)
```

All five must pass before the plan is considered resumed.

## Notes on Existing Tests

`tests/unit/plugins/test_plugin_config_validation.py` only validates `plugin/.claude-plugin/marketplace.json` (the attune-ai plugin's own file, via `PLUGIN_ROOT`). It does **not** touch the repo-root `.claude-plugin/marketplace.json`, so editing the root marketplace will not break any existing test — but it also leaves the root marketplace untested. A follow-up task could add a lightweight validator for the root marketplace (verify both plugin entries exist, source paths resolve, versions match their respective plugin.json files). Not in scope for this resume.

## Open Questions

- Should the root marketplace's top-level `metadata.description` be widened to mention both plugins? Currently it only describes `attune-ai`. Leaving it unchanged for now — `metadata` describes the marketplace itself, and per-plugin descriptions are what Claude surfaces to users. Flag for user review.
