# Plan B — Restore Runbook (Plugin State)

Purpose: reinstall `attune-ai` and re-add the marketplaces that
[scrub-runbook.md](scrub-runbook.md) removed. Run this after the
manual test plan is complete.

---

## What gets restored

| Plugin | Marketplace | Pre-scrub version |
|---|---|---|
| `attune-ai` | `attune-ai` (github: Smart-AI-Memory/attune-ai) | 5.1.1 |

| Marketplace | Source |
|---|---|
| `attune-ai` | github: Smart-AI-Memory/attune-ai |
| `attune-lite` | github: Smart-AI-Memory/attune-lite (optional — see note) |

**Note on `attune-lite`:** it had no installed plugins before the
scrub and is an attune-prefixed stale marketplace. You can safely
skip restoring it. If you want identical pre-scrub state for audit
purposes, the command is listed below, but practical restoration
only needs `attune-ai`.

---

## Restore commands

Run these in a Claude Code session after testing is done.

### 1. Clean up the test scratch marketplaces (if still added)

If Step 8 of the test plan left either scratch marketplace
attached to the session, remove them first so the restored
state is tidy:

```
/plugin uninstall attune-help@attune-docs-scratch
/plugin uninstall attune-author@attune-docs-scratch
/plugin uninstall attune-help@attune-docs-scratch-dup
/plugin marketplace remove attune-docs-scratch
/plugin marketplace remove attune-docs-scratch-dup
```

Any commands that report "not installed" / "not found" are
safe — they just mean the test plan already cleaned up.

### 2. Re-add the attune-ai marketplace

```
/plugin marketplace add Smart-AI-Memory/attune-ai
```

Expected: marketplace `attune-ai` added.

### 3. Reinstall attune-ai plugin

```
/plugin install attune-ai@attune-ai
```

Expected: plugin installed. This will pull the current HEAD of
Smart-AI-Memory/attune-ai — if a version later than 5.1.1 has
been released since the scrub (2026-04-09), you will land on
the newer version, which is fine.

### 4. (Optional) Re-add the stale attune-lite marketplace

Only do this if you want byte-identical pre-scrub state:

```
/plugin marketplace add Smart-AI-Memory/attune-lite
```

(No plugin install — the marketplace had no installed plugins
before the scrub.)

### 5. Verify restored state

```
/plugin list
```

Expected: contains `attune-ai@attune-ai` alongside the two
plugins that were never removed
(`cowork-plugin-management@knowledge-work-plugins` and
`plugin-dev@claude-plugins-official`).

```
/plugin marketplace list
```

Expected: `attune-ai`, `claude-plugins-official`,
`knowledge-work-plugins` (and `attune-lite` if you restored
it in step 4).

```
/mcp
```

Expected: the attune-ai MCP server is back alongside any
pre-existing servers.

---

## Blocker 1 — Sub-package PyPI status (RESOLVED 2026-04-10)

Both sub-packages are published and functional on PyPI:

| Package | Version | `[plugin]` extra | MCP server |
|---|---|---|---|
| `attune-help` | 0.3.1 | Working | `attune_help.mcp.server` |
| `attune-author` | 0.1.0 | Working | `attune_author.mcp.server` |

CI: Both repos (`Smart-AI-Memory/attune-help`,
`Smart-AI-Memory/attune-author`) have `publish.yml` with OIDC
trusted publishing, triggered on GitHub release or manual
dispatch. No tags exist yet — create a release in each repo
when the next version is ready.

Cleanup done:
- Removed stale `publish-attune-help.yml` from main repo
  (pointed to tombstoned `packages/attune-help/` directory)
- Cleared stale `site-packages/attune/` namespace dir that
  shadowed the editable install

---

## If restore fails

1. Check the backup location from the scrub runbook:
   `/tmp/attune-docs-scratch/plugin-state-backup-20260409-063036/`
2. Those files show the exact pre-scrub state of
   `installed_plugins.json` and `known_marketplaces.json`. Use
   them as a reference, not as a replacement.
3. If `/plugin install attune-ai@attune-ai` fails with a clone
   error, check `gh auth status` and confirm the repo is still
   reachable.
4. If the marketplace add succeeds but install fails with a
   version mismatch, try the explicit version:
   `/plugin install attune-ai@attune-ai@5.1.1` (syntax may vary —
   `/plugin install --help` will show the exact form).
