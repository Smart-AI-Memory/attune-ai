# Plan B — Scrub Runbook (Plugin State)

Purpose: temporarily remove all `attune-*` plugin state from this
machine so the manual test plan in
[manual-test-plan.md](manual-test-plan.md) can run from a "clean"
environment. Pairs with [restore-runbook.md](restore-runbook.md).

**Read this once end-to-end before running anything.**

---

## Snapshot of current state (captured 2026-04-09 06:30)

### Installed plugins

| Plugin | Marketplace | Version | Action |
|---|---|---|---|
| `cowork-plugin-management` | knowledge-work-plugins | 0.2.2 | keep |
| `plugin-dev` | claude-plugins-official | 55b58ec6e564 | keep |
| `attune-ai` | attune-ai | 5.1.1 | **scrub** |

### Known marketplaces

| Marketplace | Source | Action |
|---|---|---|
| `claude-plugins-official` | anthropics/claude-plugins-official | keep |
| `knowledge-work-plugins` | anthropics/knowledge-work-plugins | keep |
| `attune-lite` | Smart-AI-Memory/attune-lite | **scrub** (stale, no plugins installed, attune-prefixed) |
| `attune-ai` | Smart-AI-Memory/attune-ai | **scrub** |

### Backup location

Plugin state files were copied before touching anything:

```
/tmp/attune-docs-scratch/plugin-state-backup-20260409-063036/
├── installed_plugins.json
└── known_marketplaces.json
```

If anything goes wrong, the restore runbook reinstalls via
`/plugin` commands. These backup files are a last-resort fallback
for manually inspecting prior state — **do not copy them back
into `~/.claude/plugins/` directly** unless everything else has
failed, since Claude Code maintains related state in
`~/.claude/plugins/cache/` and the marketplace mirrors.

---

## Prerequisites

- Close the current Claude Code session (the one this runbook
  was prepared in). The `/plugin` commands manipulate session
  plugin state and the test plan explicitly requires a separate
  session.
- Open a new Claude Code session in any directory (project
  doesn't matter — plugin state is user-level). The attune-ai
  project directory is fine.

---

## Scrub commands

Run these in order in the new Claude Code session. Each is a
user-invoked slash command you type at the prompt, not a shell
command.

### 1. Verify starting state

```
/plugin list
```

Expected output contains:

- `attune-ai@attune-ai` (will be removed)
- `cowork-plugin-management@knowledge-work-plugins` (will stay)
- `plugin-dev@claude-plugins-official` (will stay)

```
/mcp
```

Note which MCP servers are listed. The `attune-ai` one will
disappear after uninstall; anything else should persist.

### 2. Uninstall attune-ai plugin

```
/plugin uninstall attune-ai@attune-ai
```

Expected: confirmation that attune-ai is uninstalled.

### 3. Remove the attune-ai marketplace

```
/plugin marketplace remove attune-ai
```

### 4. Remove the stale attune-lite marketplace

```
/plugin marketplace remove attune-lite
```

(No plugin was installed from this one, so no uninstall step
needed. It's scrubbed because the test plan requires "no
attune-* plugins installed" and this marketplace is
attune-prefixed.)

### 5. Verify clean state

```
/plugin list
```

Expected: **no lines starting with `attune-`**. Only these
should remain:

- `cowork-plugin-management@knowledge-work-plugins`
- `plugin-dev@claude-plugins-official`

```
/plugin marketplace list
```

Expected: no `attune-*` marketplaces. Only:

- `claude-plugins-official`
- `knowledge-work-plugins`

```
/mcp
```

Expected: no attune-related MCP servers.

### 6. Proceed to the test plan

The environment now matches the prerequisites of
[manual-test-plan.md](manual-test-plan.md). Run Step 1
(duplicate-plugin sandbox test) first, then Step 8
(end-to-end funnel tests).

**Both scratch marketplaces are ready:**

- `/tmp/attune-docs-scratch/step3-relative/` — name
  `attune-docs-scratch`, lists `attune-help` and
  `attune-author` (plugin sources point at local paths in
  `/Users/patrickroebuck/attune-ai/packages/`).
- `/tmp/attune-docs-scratch/step3-dup/` — name
  `attune-docs-scratch-dup`, same plugin list, different
  marketplace name. Used for step 1's duplicate condition.

---

## When the test plan is complete

Run [restore-runbook.md](restore-runbook.md) to reinstall
`attune-ai` and re-add the marketplaces. Do this **in the same
session you ran the tests in**, or in any fresh session after
tests are done.

## If something goes wrong mid-scrub

- If a `/plugin uninstall` fails, run `/plugin list` and note
  the exact plugin ID. The ID must match the
  `name@marketplace` format.
- If `/plugin marketplace remove` complains about plugins
  still installed from it, uninstall those plugins first,
  then retry the marketplace removal.
- Nothing destructive touches git, the repo, or the project
  directory. The scrub is confined to `~/.claude/plugins/`
  state files managed by Claude Code.
